# The model can offer a line for the global instructions; the person's Save writes it (shipped)

Why: a preference the user stated ("always use our template") lived only in that conversation;
the user had to open Settings and type it into the global instructions themselves. Claude Code
saves such a line when asked; here the model may only propose it.

## Shipped
- `remember(line)` (`tools/bookkeeping/interaction.py`): a respond-only tool like
  `ask_user_question`, so its body never runs and no approval mode or auto reviewer answers it.
  It is deferred (found through `search_tools`), not bound from the first request.
- `conversation/approvals.py`: the call shows the existing question card ("Save this to your
  global instructions...?" with the line, Save / Don't save). Only Save appends `- <line>` to
  `Settings.memory_path`; any other answer, a closed card or an unattended run writes nothing.
  Sub-agents never get it (question tools stay with the parent).
- Tests: `tests/web/test_chat_questions.py` (Save appends the line; Don't save leaves the file
  as it was).
- `ARCHITECTURE.md`, `office-agent/README.md` (Memory) say how a line gets in.

## Not verified
- The card in the running app: it is the existing question card with new text, not new UI.
- How often a real model offers a line, and whether it offers too often: needs live use.
