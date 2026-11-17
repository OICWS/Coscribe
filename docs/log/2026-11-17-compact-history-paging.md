# Compacted history loads without consuming every checkpoint (shipped)

Why: opening earlier messages after compaction requested unbounded graph history.
LangGraph eagerly reads that history before yielding its first snapshot, and the SQLite
saver holds a shared lock while reading it, delaying unrelated conversations too.

## Shipped
- Earlier-message lookup reads one checkpoint at a time, stopping at the first unseen epoch
  and releasing the shared database lock between reads. Existing chronological replay and
  multiple-compaction pagination are preserved.
- Replaying current history resets the pagination cursor, so switching away and returning
  can load the same original messages again instead of retaining an exhausted cursor.
- Regression tests verify bounded underlying SQLite history queries, repeated compactions,
  switching to another conversation, returning, and preservation of uploaded image data,
  thread IDs and explicitly saved titles. Both new checks fail against the old implementation.

## Not verified
- The reported apparent rename to a workflow investigation title was not reproduced.
  Compaction does not write title files; the tests preserve distinct original/repair titles.
- The user's actual checkpoint database and a real Windows desktop.

## Follow-ups
- Investigate the reported ordinary conversation changing to an investigation-style title
  against the affected conversation's records; this was not reproduced locally.
