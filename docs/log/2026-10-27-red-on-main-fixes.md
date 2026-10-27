# Red checks on main turned green (shipped)

Why: the Windows `pytest` job and the E2E job were red on `main` for every PR (seen on #668
and #672), and the maintainer merges only green PRs.

## Shipped
- A Doc's kept version is put back byte for byte (`tools/office/doc/history.py`). It was read
  back as text, which turns a Windows file's CRLF into LF, so the file put back had another
  version than the one asked for and redo failed. Seen on Windows as
  `test_versions_are_kept_in_the_side_folder_and_one_can_be_put_back` and
  `test_a_change_made_behind_the_editor_can_be_undone_and_done_again_lg`. A new test writes
  CRLF on any platform (`test_a_version_with_windows_line_endings_is_put_back_byte_for_byte`).
- `tests/web/test_libreoffice_routes.py`: the fake LibreOffice is a batch file on Windows, where
  a shell script cannot run, so the download test reads its version there too.
- `test_lifespan_backgrounds_a_slow_mcp_connect_instead_of_blocking_startup`: its fake connect gave up after 10 s, which a loaded Windows runner took just to start the app, so the connect "finished" before it was released. The limit is now 120 s; it only frees the thread when the test fails first.
- `test_an_expired_oauth_sign_in_is_refreshed_without_the_browser`: the refreshed token lived 1 s
  as well, so a reconnect that took longer on a loaded runner had its token expire mid-way. Only
  the first token is short-lived now.
- `docx-review.spec.ts`: "Ask Coscribe" opens the ask box since #660, so the spec picks
  "Make it shorter" and checks that the instruction goes with the quoted words.

## Not verified
- The two Windows fixes on a Windows machine before CI runs them: the batch-file launcher and
  the CRLF restore were checked on Linux only (the CRLF test fails there without the fix).
