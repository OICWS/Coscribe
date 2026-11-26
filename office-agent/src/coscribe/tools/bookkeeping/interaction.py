"""The interaction tools: what the Coordinator asks or offers the person in the conversation.

ask_user_question shows clickable choices for the same reason Claude Code's own
AskUserQuestion exists: a fixed option set steers toward an answer that's actionable, and a
click is faster than a sentence. It doesn't wait: the card stays in the conversation, the model
goes on with what doesn't depend on the answer or ends its turn, and a person who is reading or
busy isn't held up; they answer whenever, by a click or in their own words (decision 0060). A
click comes back as their next message; a reply in their own words gets a note naming the open
card (conversation/turn_text.py), and answer_question_card records how it answered.

The rest (exit_plan_mode, remember, request_folder_access, install_package) never run their own
body: they're routed through LangGraph's HumanInTheLoopMiddleware with
`allowed_decisions=["respond"]` (conversation/approvals.py's _decide_action_request and
runtime_lg/agent.py's `question_tool_names`), and the person's answer is substituted as the
call's result. Their bodies raise, so a graph that failed to register one fails loudly instead
of hanging.

Not given to sub-agents (runtime_lg/subagents.py): a question belongs to the person talking to
the parent, not to a delegated run.
"""

import unicodedata
from collections.abc import Callable, Mapping, Sequence
from typing import Annotated, Any, Literal, NotRequired

from pydantic import Field

# pydantic needs typing_extensions' TypedDict before Python 3.12.
from typing_extensions import TypedDict

from ...runtime import tool_metadata

QUESTION_TOOL_NAMES: frozenset[str] = frozenset(
    {"exit_plan_mode", "install_package", "remember", "request_folder_access"}
)

QUESTIONS_SHOWN = (
    "The questions are on a card in the conversation; the person answers when they choose, by "
    "a click (it arrives as their next message) or in their own words. Don't guess the answer. "
    "If the rest of the work depends on it, end your turn now without repeating the questions. "
    "If some of it doesn't, go on with that part only, and say in one line what waits on the "
    "answer."
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
    recommended: NotRequired[
        Annotated[bool, Field(description="true on the one option you'd pick; at most one")]
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

    Do the work that doesn't depend on the answer first, then ask
    everything you need at once (1-4 questions). Each option has a short
    label and, when the label alone doesn't say enough, a one-line
    description; mark the one you'd pick as recommended. The user can
    always answer in their own words instead, so the options narrow the
    likely answers without having to be exhaustive.

    The questions show as a card in the conversation and this call
    returns at once; the user answers when they choose, as a later
    message. Until then do only work that doesn't depend on the answer,
    or end your turn.

    Args:
        questions: the questions, in the order to ask them
    """
    return QUESTIONS_SHOWN


def answer_question_card(answers: list[str]) -> str:
    """Record that the user's own words answered your open question card,
    so the card closes and shows their answers. Call it first, before
    other work, when their message carries the note that a card is open
    and, with what they said before, it settles every question on it. A
    question they leave to you ("anything", "you decide") is settled:
    record the choice you make. When some questions are still open,
    don't call it yet: ask about those in a sentence of your reply, not
    with a new card, and call it with every answer once their later
    words settle the rest. When their message is about something else,
    don't call it either.

    Args:
        answers: one per question on the card, in order: the option's
            label when their words pick one or they leave it to you and
            you pick one, otherwise their answer (or your choice) in a
            few words in their language.
    """
    if not answers or any(not answer.strip() for answer in answers):
        raise ValueError(
            "Every question needs an answer: the card closes only once all are answered. "
            "Ask about the rest in your reply instead."
        )
    return "The card is closed and shows their answers."


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
                recommended = option.get("recommended") is True
            else:
                label, description, recommended = str(option), "", False
            if label.strip():
                options.append(
                    {
                        "label": label.strip(),
                        "description": description.strip(),
                        "recommended": recommended,
                    }
                )
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
    arguments: none of them needs workspace, thread or state_dir access."""
    return [
        tool_metadata(ask_user_question, risk_category="READ", category="interaction"),
        tool_metadata(answer_question_card, risk_category="READ", category="interaction"),
        tool_metadata(exit_plan_mode, risk_category="READ", category="interaction"),
        tool_metadata(remember, risk_category="READ", category="interaction"),
        tool_metadata(request_folder_access, risk_category="READ", category="interaction"),
        tool_metadata(install_package, risk_category="READ", category="interaction"),
        tool_metadata(
            react_to_message, risk_category="READ", category="interaction", ends_turn=True
        ),
    ]
