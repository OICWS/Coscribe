# Older tool results are left out of what the model is sent, before a conversation needs compacting (shipped)

Why: most of a long office conversation is tool output the model has already
used (a document read in full, search hits, a script's printout), and it filled
the context window until compaction summarized everything. Part of #805.

## Shipped
- `runtime_lg/context_editing.py`: a LangChain `ContextEditingMiddleware` with
  our own edit. Once the request passes half the auto-compact size, tool
  results older than the newest 6 are replaced with a note that says to call
  the tool again. The boundary moves in steps of 8 results, so a provider's
  cached prefix is lost about once every 8 tool calls rather than on every one
  (LangChain's `ClearToolUsesEdit` moves it on each call).
- Never cleared: the plan (`task_*`), answers (`ask_user_question`,
  `remember`), skills, sub-agent reports, `review_work` and `search_tools`.
- Only the request is edited; the history keeps every result, so compaction
  and `/compact` still summarize them whole. It runs only where auto-compact
  does (the top-level conversation, not sub-agents).

## Not verified
- How often a real model re-runs a cleared tool, and the cache hit rate with a
  real provider over a long conversation.
- A real Windows machine.

## Follow-ups
- Measure re-reads and cache hits on a long live conversation before changing
  `KEEP`/`STEP`.
