# The model can answer a message with an emoji instead of words (shipped)

Why: when the model asks "shall I also change the subtitle?" and the person says "no, thanks", the
only answer it had was a line of filler ("OK") taking a row of the chat. A reaction on the
person's message says the same without one.

## Shipped
- `react_to_message(emoji)` in `tools/bookkeeping/interaction.py`, a core tool
  (`coordinator.py`'s `CORE_TOOL_NAMES`), not given to sub-agents or workflow steps. Its docstring
  is the only guidance: use it when words would only acknowledge.
- `ToolMetadata.ends_turn`: `runtime_lg/agent.py` binds such a tool with `return_direct`, so a
  step that calls only it ends the turn with no further model call; called next to other tools
  the turn goes on. `conversation/turn_stream.py` then sends an empty reply instead of the
  "[no reply ...]" note, and the chat draws nothing for it.
- The chat shows the emoji on the lower left corner of the user's bubble, the call taken out of
  the tool rows (`frontend/src/lib/reactions.ts`); a reload shows it again from the history.
- Checked live with DeepSeek (deepseek-flash), each conversation reloaded before reading it:
  "不用了，谢谢" after a question got 👍 in 3 of 3 runs, "好的" after a list got 👍; "明白了，谢谢"
  after an explanation got 😊 once and "不客气" twice; a question, and a "no, but do X instead"
  that needs work, got words and no reaction.

## Not verified
- On Windows in the desktop app; with models other than deepseek-flash.
