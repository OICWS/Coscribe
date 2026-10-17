# Windows night 2: four fixes for five failing tests (shipped)

Why: the nightly Windows run of 10-16 was red (5 failed, issue #339), so the 14-day clock
restarted.

## Shipped
- A deck built from page files saved with CRLF (what Windows writes) was never previewed from its
  SVG pages: the build hashed the text after Python's newline translation, `built_pages` hashed
  the raw bytes, so the pages always looked edited since the build and the preview fell back to
  "needs Microsoft Office". `built_pages` now hashes the text the way the build does. This is a
  product bug, not only a test one: on Windows no model-written deck got its preview. The new test
  writes CRLF pages on any platform and fails without the fix; it fixes three of the five.
- `test_a_file_name_never_becomes_part_of_the_script` named its file with `C:\` in it, which
  Windows does not allow in a file name; the injection text stays (`'; Remove-Item -Recurse
  -Force; '`).
- `test_deleting_a_task_deletes_its_run_conversations_lg`: the wait helper returned after 5 s
  even when the run was still going, so the delete could land before the run's last checkpoint
  write and the conversation came back. The helper waits up to 30 s and the test asserts the run
  ended. Not reproduced on Linux (it passed every time); the cause is inferred from the helper
  returning on timeout without a check.
- `test_a_background_sub_agent_waits_for_approval_after_the_tab_closes` (first seen on this PR's
  Windows run): the sub-agent task store replaced its `.tmp` file with a bare `os.replace` while
  `list_for_thread` had the file open, and Windows answered "Access is denied", failing the run.
  It now uses `replace_with_retry`, as the task store already did.

## Not verified
- All of it on Windows until this PR's Windows run (the workflow file carries a comment change
  to trigger it). The scheduled-task test in particular is a guess at a timing cause.
