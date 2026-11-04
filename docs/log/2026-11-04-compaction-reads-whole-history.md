# Compaction summarizes the whole history and keeps the open tasks (shipped)

Why: the automatic compaction used LangChain's `SummarizationMiddleware` with its defaults.
Those summarize only the last 4,000 tokens of what is dropped (`trim_tokens_to_summarize`,
checked in langchain 1.4.8), so at the first compaction of a long conversation the user's first
request, early decisions and the files made early on were gone. The kept tail was 20 messages
whatever their size.

## Shipped
- `runtime_lg/agent.py`: `_CompactMiddleware` summarizes everything it replaces (no trim; the
  replaced part is about the trigger's size, under the context window), keeps a tail of one
  eighth of the trigger in tokens, and uses coscribe's own summary prompt.
- `runtime/compaction.py`: one prompt for /compact and the automatic compaction, with fixed
  sections: requests (in the user's words), decisions and constraints, files with paths, facts
  found by tools, current work.
- After either summary, the conversation's unfinished tasks follow as a note
  (`TaskToolkit.open_tasks_note`), read from the task store rather than from the transcript.
- Tests: `tests/test_runtime_lg_agent.py` (the summary call is shown the first request of a
  long thread; the task note follows the summary), `tests/web/test_chat_history.py` (/compact's
  note ends with the open tasks).

## Not verified
- A real long conversation on a real provider reaching the trigger; the summary's quality was
  not measured with `evals/` (it calls a model).

## Follow-ups
- Clearing old tool results before compaction (`ContextEditingMiddleware`), a shorter system
  prompt, large script output saved to a file, sub-agent kinds, memory proposals: each its own PR.
