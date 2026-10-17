# Windows night 3: five tests written on Linux, fixed for Windows (shipped)

Why: the nightly Windows run of 10-17 (run 27) was red with 5 failures, so the 14-day clock
restarted again. All five are tests added after #340, none a product bug.

## Shipped
- `test_deck_view`: a page was rewritten with `write_text` and no encoding, so Windows used cp1252
  and could not encode the Chinese in it. It writes UTF-8, like the line that reads it.
- `test_components_map` (two tests): the paths it compared were `str(Path)`, with backslashes on
  Windows, against forward slashes in `components.toml`. They use `as_posix()`.
- `test_approval_decisions` (two rows): the folder list the reviewer is shown is in the platform's
  own form. The test compares it with forward slashes, and the default-workspace row now checks the
  real workspace path instead of a leading `/`.

## Not verified
- On Windows until this PR's Windows run (the workflow file carries a comment change to trigger
  it). The three files pass on Linux.
