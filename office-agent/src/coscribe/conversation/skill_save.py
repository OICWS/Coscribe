"""/saveskill: the curator proposes a skill from the conversation, may ask a few
clarifying questions, and writes it once the person confirms. It lives apart from
ChatSessionLG because it is a small dialogue of its own that takes over the next
messages; the session keeps the pending state and decides when a message goes here.
"""

from __future__ import annotations

from typing import Any, Protocol

from ..config import Settings
from ..runtime_lg import SkillSaveProposal, propose_skill_save_lg, write_skill_lg
from ..tools import load_builtin_skills, slugify_skill_name
from .events import EventSink

# How many rounds of clarifying question/answer /saveskill goes through
# before giving up.
MAX_SAVE_CLARIFICATION_ROUNDS = 3


class SkillSaveHost(Protocol):
    """What the dialogue reads and calls on the session it saves a skill for."""

    settings: Settings
    model: Any
    enabled_skill_names: set[str]
    pending_save_skill_proposal: dict[str, Any] | None

    async def _current_messages(self) -> list[Any]: ...

    async def set_enabled_skills(
        self, skill_names: set[str], websocket: EventSink, *, announce: bool = True
    ) -> None: ...


class SkillSave:
    def __init__(self, host: SkillSaveHost) -> None:
        self._host = host

    async def _handle_save_skill(self, name: str, websocket: EventSink) -> None:
        """/saveskill's own entry point: validate the name, require a
        non-empty conversation, run one curator round
        (propose_skill_save_lg), present it."""
        name = name.strip()
        if not name:
            await websocket.send_json({"type": "error", "message": "Usage: /saveskill <name>"})
            return
        messages = await self._host._current_messages()
        if not messages:
            await websocket.send_json({"type": "error", "message": "Nothing to save yet."})
            return
        proposal = await propose_skill_save_lg(
            name, messages=messages, model=self._host.model, clarification_history=[]
        )
        self._host.pending_save_skill_proposal = await self._present_skill_save_proposal(
            name, proposal, [], 1, websocket
        )

    async def _present_skill_save_proposal(
        self,
        name: str,
        proposal: SkillSaveProposal,
        clarification_history: list[tuple[str, str]],
        rounds: int,
        websocket: EventSink,
    ) -> dict[str, Any]:
        """Same "plain chat bubble, not a new WS event type" reasoning as
        _present_save_proposal -- the description/body preview is shown
        in full (not truncated) for the same reason a script's full text
        is shown before a run_python_script approval: this is exactly
        the kind of content worth reading before confirming a write, not
        something to skim a summary of."""
        if proposal.decision == "clarify":
            await websocket.send_json({"type": "agent_message", "text": proposal.question})
            return {
                "name": name,
                "stage": "clarify",
                "question": proposal.question,
                "clarification_history": clarification_history,
                "rounds": rounds,
            }
        slug = slugify_skill_name(name)
        overwrite_note = ""
        if (self._host.settings.skills_dir / slug / "SKILL.md").is_file():
            overwrite_note = " (this will overwrite the existing skill at this slug)"
        text = (
            f'Proposed skill "{name}" (/{slug}){overwrite_note}:\n'
            f"{proposal.description}\n\n"
            f"{proposal.body}\n\n"
            'Save this? Reply "yes" to save, anything else to discard.'
        )
        await websocket.send_json({"type": "agent_message", "text": text})
        return {
            "name": name,
            "stage": "confirm",
            "proposal": proposal,
            "clarification_history": clarification_history,
        }

    async def _handle_pending_skill_save_proposal(self, text: str, websocket: EventSink) -> None:
        """While pending_save_skill_proposal is set, every incoming message
        answers the curator's clarifying question or confirms/discards its
        proposed save instead of running a normal turn."""
        proposal_state = self._host.pending_save_skill_proposal
        assert proposal_state is not None
        if proposal_state["stage"] == "clarify":
            answer = text.strip()
            if not answer:
                await websocket.send_json(
                    {
                        "type": "agent_message",
                        "text": "(please answer, or say 'cancel' to abandon this save)",
                    }
                )
                return
            if answer.lower() == "cancel":
                self._host.pending_save_skill_proposal = None
                await websocket.send_json({"type": "agent_message", "text": "Cancelled."})
                return
            name = proposal_state["name"]
            history = [
                *proposal_state["clarification_history"],
                (proposal_state["question"], answer),
            ]
            rounds = proposal_state["rounds"]
            if rounds >= MAX_SAVE_CLARIFICATION_ROUNDS:
                self._host.pending_save_skill_proposal = None
                await websocket.send_json(
                    {
                        "type": "agent_message",
                        "text": "Still unclear after a few tries -- try /saveskill again "
                        "with a more specific name, or once the conversation has a "
                        "clearer single task in it.",
                    }
                )
                return
            messages = await self._host._current_messages()
            proposal = await propose_skill_save_lg(
                name, messages=messages, model=self._host.model, clarification_history=history
            )
            self._host.pending_save_skill_proposal = await self._present_skill_save_proposal(
                name, proposal, history, rounds + 1, websocket
            )
            return

        # stage == "confirm"
        answer = text.strip().lower()
        name = proposal_state["name"]
        proposal = proposal_state["proposal"]
        self._host.pending_save_skill_proposal = None
        if answer not in {"y", "yes"}:
            await websocket.send_json(
                {
                    "type": "agent_message",
                    "text": "Discarded -- refine your request and try /saveskill again.",
                }
            )
            return
        slug = slugify_skill_name(name)
        # A slug colliding with a *built-in* skill would silently shadow
        # it for every future /<slug> lookup (skills_by_slug below keeps
        # whichever of load_builtin_skills()/load_skills() loads last for
        # a repeated key) -- refused outright rather than allowed to
        # overwrite-in-spirit a file this session doesn't even own.
        # Colliding with an existing *user* skill is fine (see
        # write_skill_lg's own docstring) -- that's this command's own
        # "update" path, same as Skill Creator's own guidance.
        if slug in {s.slug for s in load_builtin_skills()}:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"/{slug} is already a built-in skill -- choose a "
                    "different name for /saveskill.",
                }
            )
            return
        saved = write_skill_lg(
            name,
            proposal.description or "",
            proposal.body or "",
            skills_dir=self._host.settings.skills_dir,
        )
        await websocket.send_json(
            {"type": "skill_saved", "name": saved["name"], "slug": saved["slug"]}
        )
        # Refreshes the session's lg_agent/instructions/tools AND skills_by_slug
        # from disk (set_enabled_skills' own rebuild already reloads both
        # load_builtin_skills()+load_skills(settings.skills_dir) fresh) --
        # without this, the just-saved skill wouldn't actually be usable
        # (either passively or via /<slug>) until this session reconnects,
        # which would make "yes" feel like it silently did nothing.
        await self._host.set_enabled_skills(
            self._host.enabled_skill_names | {saved["name"]}, websocket
        )
