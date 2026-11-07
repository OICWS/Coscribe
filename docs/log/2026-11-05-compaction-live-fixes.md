# What a live run on deepseek-flash found in compaction and remember, fixed (shipped)

Why: a live check of #804-#810 on deepseek-flash, with the auto-compact threshold lowered so a
short conversation reaches it, showed four things a person would see go wrong.

## Shipped
- The automatic compaction's summary no longer streams to the tab as if it were the reply:
  `conversation/turn_stream.py` drops chunks LangChain tags `lc_source: summarization`.
- Tool calls that ran before a compaction are no longer announced as starting again:
  `announce_started_tools` reads only the model node's update, since the compaction's update
  re-adds the kept tail.
- A second compaction keeps the first one's requests: `COMPACT_INSTRUCTIONS` says an earlier
  summary at the top is the record of everything before and is carried forward. Live, the
  second summary had read it as "no explicit request" and the model re-created its plan.
- `remember` offered the same preference twice (first in Chinese, then in English) and both
  were saved: its description now says to offer a preference once, in the language the user
  wrote in, and the saved result says not to offer it again.

## Not verified
- Only deepseek-flash; a real Windows machine.

## Follow-ups
- None.
