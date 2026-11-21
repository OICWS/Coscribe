"""ask_user_question -- lets the Coordinator ask a clarifying question with
clickable choices instead of only asking in prose, for exactly the same
reason Claude Code's own AskUserQuestion tool exists: a fixed option set
steers the user toward an answer that's actually actionable, and a click is
faster than typing a full sentence.

Unlike every other tool in this package, this one never actually runs its
own Python body. It's routed through LangGraph's HumanInTheLoopMiddleware
with `allowed_decisions=["respond"]` (see conversation/session.py's
_decide_action_request and runtime_lg/agent.py's `question_tool_names`) --
the interrupt always fires, and the human's answer (typed via
web/app.py's `question_response` message, or a stop/disconnect's own
placeholder) is substituted directly as this call's result, the tool
function itself never executing. The body below is a defensive
RuntimeError, not a real implementation: reaching it means something
failed to wire this tool into `question_tool_names` for whichever graph
called it, and that should fail loudly, not hang forever waiting on a
Future nobody will ever resolve.

Not given to sub-agents (runtime_lg/subagents.py's _NOT_FOR_SUBAGENTS):
a question belongs to the person talking to the parent, not to a
delegated run.
"""

import unicodedata
from collections.abc import Callable, Mapping, Sequence
from typing import Annotated, Any, Literal, NotRequired

from pydantic import Field

# pydantic needs typing_extensions' TypedDict before Python 3.12.
from typing_extensions import TypedDict

from ...runtime import tool_metadata

QUESTION_TOOL_NAMES: frozenset[str] = frozenset(
    {"ask_user_question", "exit_plan_mode", "install_package", "remember", "request_folder_access"}
)

# exit_plan_mode's answers, as the frontend sends them.
PLAN_CHOICE_AUTO = "auto"
PLAN_CHOICE_MANUAL = "manual"
PLAN_CHOICE_REVISE = "revise:"
PLAN_CHOICE_REJECT = "reject"


class QuestionOption(TypedDict):
    label: Annotated[str, Field(description="a few words -- what the user clicks")]
    description: NotRequired[
        Annotated[str, Field(description="one short line under the label: what picking it means")]
    ]


class UserQuestion(TypedDict):
    question: Annotated[str, Field(description="the question, one sentence")]
    options: Annotated[list[QuestionOption], Field(description="2-6 choices")]
    multi_select: NotRequired[
        Annotated[
            bool,
            Field(
                description='true when several can apply ("which sheets should I include?"); '
                'false when exactly one makes sense ("which format?")'
            ),
        ]
    ]
    header: NotRequired[
        Annotated[str, Field(description='a label of a few words for the question, e.g. "Style"')]
    ]


def ask_user_question(questions: list[UserQuestion]) -> str:
    """Ask the user clarifying questions with clickable choices, instead
    of only asking in a normal reply. Use this when you're about to guess
    at a genuinely ambiguous requirement, when there's a real fork in how
    to proceed you'd otherwise describe in prose, or whenever picking
    from a short list would clearly be faster for the user than typing a
    full sentence. Don't reach for this for a plain yes/no you can just
    ask in your normal reply, or when the user's own request already
    fully specifies what to do -- this is for decisions only the user can
    make, not a substitute for actually reading what they already said.

    Ask everything you need at once (1-4 questions): the user steps
    through them one by one and answers them together. Each option has a
    short label and, when the label alone doesn't say enough, a one-line
    description. The user can always type their own answer instead
    ("Something else") or skip a question, so the options narrow the
    likely answers without having to be exhaustive.

    The answer comes back as the chosen label(s) -- several joined by
    ", " for a multi-select question -- one line per question when you
    asked more than one, "(skipped)" for a question the user skipped.

    This call always pauses for a real person to answer; there's no
    approval step and no auto-answer.

    Args:
        questions: the questions, in the order to ask them
    """
    raise RuntimeError(
        "ask_user_question must be resolved via HumanInTheLoopMiddleware's "
        "'respond' decision -- reaching this body means the graph that "
        "called it never registered it in question_tool_names."
    )


def normalize_questions(args: dict[str, Any]) -> list[dict[str, Any]]:
    """The call's questions as the page shows them. A conversation saved
    before questions came in lists asked one question with its options as
    lines of text; it can still be resumed."""
    raw = args.get("questions")
    if not isinstance(raw, list):
        raw = [
            {
                "question": args.get("question", ""),
                "header": args.get("header", ""),
                "options": str(args.get("options", "")).split("\n"),
                "multi_select": args.get("multi_select", False),
            }
        ]
    questions = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        options = []
        for option in item.get("options") or []:
            if isinstance(option, dict):
                label, description = (
                    str(option.get("label", "")),
                    str(option.get("description", "")),
                )
            else:
                label, description = str(option), ""
            if label.strip():
                options.append({"label": label.strip(), "description": description.strip()})
        questions.append(
            {
                "question": str(item.get("question", "")),
                "header": str(item.get("header", "")),
                "options": options,
                "multi_select": bool(item.get("multi_select", False)),
            }
        )
    return questions


# Closing the card while a review-or-save artifact is next reads as "not yet": a guessed
# draft would put a card in front of someone who just said they aren't sure.
QUESTIONS_DISMISSED = (
    "The user closed the questions without answering. Don't ask them again. If "
    "your next step makes something for them to review or save (a workflow draft, "
    "a scheduled task), don't make it: say in one line what you'd need to know, "
    "then stop. Otherwise go on with the most sensible choice and say which you "
    "made, or ask in your reply if you can't go on without an answer."
)

QUESTION_REPLIED = (
    "The user didn't pick an option and wrote this instead; take it as their answer:\n{reply}"
)


def format_question_answers(
    questions: Sequence[dict[str, Any]],
    reply: str | Sequence[str | None] | Mapping[str, str] | None,
) -> str:
    """The tool result the model reads. `reply` is one answer per question
    (None for a skipped one), None when the user closed the questions,
    `{"reply": text}` when they wrote in the chat instead of choosing, or
    a plain string -- a stop's placeholder, or an older page's single
    answer -- passed through as is."""
    if reply is None:
        return QUESTIONS_DISMISSED
    if isinstance(reply, Mapping):
        return QUESTION_REPLIED.format(reply=str(reply.get("reply", "")).strip())
    if isinstance(reply, str):
        return reply
    answers = [answer.strip() if answer and answer.strip() else "(skipped)" for answer in reply]
    answers += ["(skipped)"] * (len(questions) - len(answers))
    if len(questions) <= 1:
        return answers[0] if answers else "(skipped)"
    return "\n".join(
        f"{index}. {question['question']} -> {answer}"
        for index, (question, answer) in enumerate(zip(questions, answers, strict=False), 1)
    )


def exit_plan_mode(plan: str) -> str:
    """Present your plan for the user's approval before doing the work. In
    plan mode this is how planning ends. Outside it, use it first for a task
    of many steps, or one that changes many files or is hard to undo; just
    do a small task. Record the steps with task_create before calling; when
    the result gives a task list as they approved it, carry out that one.
    They choose: approve and carry it out in auto mode, approve and carry it
    out approving each change themselves, or keep planning with feedback.
    The result says which; plan mode ends when they approve.

    Args:
        plan: the plan in markdown -- what you found, the steps you'll take
            in order, the files or places each touches, and what you'll
            check at the end. Complete enough to approve without asking.
    """
    raise RuntimeError(
        "exit_plan_mode must be resolved via HumanInTheLoopMiddleware's 'respond' "
        "decision -- reaching this body means the graph never registered it in "
        "question_tool_names."
    )


def remember(line: str) -> str:
    """Offer to add one line to the user's global instructions, which are
    read into every conversation. Use it when the user states something
    that should hold from now on -- "always...", "from now on...", "remember
    that..." -- or corrects you on a preference that will come up again.
    Not for facts about the current task. The user sees the line and saves
    it or not; nothing is written unless they do, and the result says which.
    Offer a preference once: after they save or decline it, don't offer it
    again, reworded or in another language.

    Args:
        line: one short sentence, in the language the user wrote in, that makes sense
            on its own in any later conversation, e.g. "Use the company
            template in Templates/brand.pptx for every deck."
    """
    raise RuntimeError(
        "remember must be resolved via HumanInTheLoopMiddleware's 'respond' decision -- "
        "reaching this body means the graph never registered it in question_tool_names."
    )


def request_folder_access(folder: str, access: Literal["read", "write"], reason: str) -> str:
    """Ask the user to let you use a folder outside the workspace. Call it when a
    file tool refused a path as outside any allowed directory and the work needs
    that folder; don't ask for a whole drive or the home folder. The user allows it
    for every workspace or only this conversation, or declines; a write can also
    be told to save in the workspace instead. The result says which; once
    allowed, call the refused tool again.

    Args:
        folder: the absolute path of the folder, as the refusal named it.
        access: "read" to open files there, "write" to save into it as well.
        reason: one short line on what you need it for, in the language the user
            wrote in, e.g. "to read the 2025 quotes".
    """
    raise RuntimeError(
        "request_folder_access must be resolved via HumanInTheLoopMiddleware's 'respond' "
        "decision -- reaching this body means the graph never registered it in "
        "question_tool_names."
    )


def install_package(runtime: Literal["python", "node"], package: str, reason: str) -> str:
    """Ask the user to install a package your script needs into the environment
    run_python_script or run_node_script runs in. Call it when a script failed
    because a module is missing (ModuleNotFoundError, "Cannot find module"), then
    run the script again once the result says it is installed. The user installs
    or declines on a card; a declined package stays declined in this conversation.
    With nobody watching (a scheduled run) it is refused: name the missing package
    in your result instead.

    Args:
        runtime: "python" for run_python_script, "node" for run_node_script.
        package: the package's name as pip or npm knows it, optionally with one
            version, e.g. "python-docx", "openpyxl==3.1.2", "sharp@0.33.5". No
            URLs, paths, options or several packages.
        reason: one short line on what the script needs it for, in the language
            the user wrote in, e.g. "to read the .msg emails".
    """
    raise RuntimeError(
        "install_package must be resolved via HumanInTheLoopMiddleware's 'respond' decision -- "
        "reaching this body means the graph never registered it in question_tool_names."
    )


def react_to_message(emoji: str) -> str:
    """Answer the user's latest message with one emoji, shown on their message, instead of a
    written reply. Use it when words would only acknowledge: they turned down what you offered
    ("no need"), said thanks or "ok", and nothing is left to do. Called on its own it ends your
    turn, so write no text with it. Alongside other tools, carry on as usual.

    Args:
        emoji: one emoji, e.g. "👍".
    """
    if not _is_one_emoji(emoji.strip()):
        raise ValueError(f'{emoji!r} is not one emoji; pass one, e.g. "👍", or reply in words.')
    return "Reacted."


# The standard library has no grapheme clusters, so this allows what one emoji can be made of:
# pictographs and the joiners, variation selectors and skin tones between them (a family is
# about ten code points), and no letters, digits or spaces, which a word would need.
_EMOJI_MAX_CODE_POINTS = 16


def _is_one_emoji(text: str) -> bool:
    return (
        0 < len(text) <= _EMOJI_MAX_CODE_POINTS
        and any(unicodedata.category(c) == "So" for c in text)
        and not any(c.isalnum() or c.isspace() for c in text)
    )


def build_interaction_tools() -> list[Callable[..., Any]]:
    """Return the interaction tool callables. No state to bind -- unlike
    every other build_*_tools factory in this package, this one takes no
    arguments, since ask_user_question needs no workspace/thread/state_dir
    access (its whole behavior lives in the interrupt machinery, not this
    function body)."""
    return [
        tool_metadata(ask_user_question, risk_category="READ", category="interaction"),
        tool_metadata(exit_plan_mode, risk_category="READ", category="interaction"),
        tool_metadata(remember, risk_category="READ", category="interaction"),
        tool_metadata(request_folder_access, risk_category="READ", category="interaction"),
        tool_metadata(install_package, risk_category="READ", category="interaction"),
        tool_metadata(
            react_to_message, risk_category="READ", category="interaction", ends_turn=True
        ),
    ]
