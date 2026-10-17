# `scripts/review_pack.py`: the reviewer's input for one PR (shipped)

Why: #348 item 8. A review started from the raw diff; the cards, decisions, snapshots and "Not
verified" items a reviewer needs had to be found by hand.

## Shipped
- `office-agent/scripts/review_pack.py <PR>` prints Markdown: the components and cards the PR touches
  (with their interface), the invariant paths it changes (the `CODEOWNERS` block plus the files
  that open a listener), the snapshots it edits, the ratchet numbers it moves (base against head,
  a new name or a bigger number marked WORSE), the decisions its text links and every "Not
  verified" item from the PR text and the `docs/log/` entries it adds.
- It reads through `gh api` (REST) and `git`; it posts nothing.
- `tests/test_review_pack.py` covers the pieces that decide what is shown.

## Not verified
- Run by hand on #369 and #371 only; no one has reviewed from its output yet.

## Follow-ups
- The weekly metrics page and the `needs-real-machine` issues, the other two parts of item 8.
