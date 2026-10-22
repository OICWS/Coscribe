# Prompt suggestions: the next message offered in the message box (shipped)

Why: after a reply the person often sends a short, predictable follow-up. A suggestion in the
box saves typing it: Enter sends it, Tab puts it in the box to edit.

## Shipped
- `conversation/suggestions.py`: one short model call outside the agent graph (the way a
  conversation is titled), so the agent's tools and system prompt are unchanged. The model
  answers NONE when nothing is likely; a long or empty answer is dropped.
- `session.py` asks after a turn that ended normally: not stopped, no approval or question
  waiting, no steering note queued, not a scheduled run, not a report turn. A new turn cancels a
  request still running.
- New wire event `prompt_suggestion` (`wire.py`, regenerated `wire.gen.ts`).
- `Composer.tsx`: the suggestion is the textarea's placeholder (gray) while the box is empty and
  idle; Enter sends it, Tab fills it as normal text with the caret at the end, Esc or any typing
  dismisses it.
- Settings > Sessions > Prompt suggestions (`COSCRIBE_PROMPT_SUGGESTIONS`, on by default, live).
- Tests: `tests/test_suggestions.py`, two chat tests in `tests/web/test_threads.py`, reducer tests,
  `tests/e2e/prompt-suggestion.spec.ts` (the event is injected into the real socket).

## Not verified
- Quality of the suggestions with a real model: the tests use a scripted one.
- A real Windows window, and an input method editor composing while a suggestion shows (the
  keys are ignored during composition in code, not tried).

## Follow-ups
- A cheaper model for the call, if the extra usage matters.
