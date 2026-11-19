# The model can answer a message with an emoji instead of words (shipped)

Why: when the model asks "shall I also change the subtitle?" and the person says "no, thanks", the
only answer it had was a line of filler ("OK") taking a row of the chat. A reaction on the
person's message says the same without one.

## Shipped
- `react_to_message(emoji)` in `tools/bookkeeping/interaction.py`, a core tool
  (`coordinator.py`'s `CORE_TOOL_NAMES`), not given to sub-agents or workflow steps. Its docstring
  is the only guidance: use it when words would only acknowledge.
- `ToolMetadata.ends_turn`: `runtime_lg/turn_checks.py`'s `_EndsTurnMiddleware` ends the turn
  before the next model call when every call of the step was a successful one to such a tool.
  A failed call goes back to the model, and the turn-end checks (open plan tasks, an Office file
  that doesn't open) are sent to the model instead of ending. Such a result is marked
  `ends_turn` in its response_metadata, so `conversation/turn_stream.py` (also after a reconnect,
  `approval_resume.py`) sends an empty reply instead of the "[no reply ...]" note, and the chat
  draws nothing for it. The CLI prints "reacted 👍".
- The emoji is checked as one emoji: pictographs and what joins them, up to 16 code points, no
  letters, digits or spaces.
- The chat shows the emoji on the lower left corner of the user's bubble once the call has
  worked, the call taken out of the tool rows (`frontend/src/lib/reactions.ts`); a reload shows
  it again from the history. On a message drawn as a card (a run's prompt, a report) it stays a
  tool row.
- Checked live with DeepSeek (deepseek-flash), each conversation reloaded before reading it:
  "不用了，谢谢" after a question got 👍 in 3 of 3 runs, "好的" after a list got 👍; "明白了，谢谢"
  after an explanation got 😊 once and "不客气" twice; a question, and a "no, but do X instead"
  that needs work, got words and no reaction.

## Not verified
- On Windows in the desktop app; with models other than deepseek-flash.
