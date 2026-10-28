# Putting a kept Doc version back keeps its bytes (shipped)

Why: the Windows night of 10-27 failed three tests, which restarts the 14-night clock of #232 (7 of 14 before it).

## Shipped
- `tools/office/doc/history.py`, `files.py`: `restore_version` read the kept version as text and wrote it back as UTF-8, so on Windows a file saved with CRLF came back with LF and its version hash no longer matched the one that was kept. It now copies the kept bytes. Two tests failed on this (`test_versions_are_kept_in_the_side_folder_and_one_can_be_put_back`, `test_a_change_made_behind_the_editor_can_be_undone_and_done_again_lg`).
- `tests/web/test_libreoffice_routes.py`: `test_a_download_runs_in_the_background_and_leaves_a_copy` fakes the launcher with a shell script, which Windows cannot start, so the version stayed None. It is skipped on Windows with the same reason `tests/test_libreoffice.py` gives.
- `docs/plan.md`: the Windows line records the night and that the count restarts at 0.

## Not verified
- Only checked on Linux locally; a manual Windows run on the fix branch is the check.
- The skipped test leaves the download route's version display untested on Windows.

## Follow-ups
- A Windows-native fake launcher (a `.com` or `.exe`) would let that test run there.
