# The Word review routes stop returning library and OS error text (shipped)

Why: batch 10 item 2 (#425) asked for the routes that hand an exception's text to the client to use a fixed message for anything that is not ours, as #422 did for the slides routes. The three `docx-review` routes in `web/routes/threads.py` returned `str(exc)` for `zipfile.BadZipFile` (the standard library's text) and `PermissionError` (the OS's text, which carries the file's path).

## Shipped
- `BadZipFile` answers `That file is not a valid Word document.` and `PermissionError` answers that Coscribe cannot change the file (open in Word, or outside the folders it may write to). A `ValueError` is the review code's own message (`unknown op`, `no tracked change with id ...`) and stays.
- `test_the_word_review_routes_read_act_on_and_show_the_original_lg` checks both messages; a `PermissionError` carrying a path is injected into the edit call. Checked by breaking: returning `str(exc)` for `BadZipFile` fails it.

## Not left
- The other `str(exc)` routes in `threads.py` return messages of our own exception types (`DraftFailed`, `SecretError`, `MessagingError`, `KeyError` of our stores, `ValueError` of the group store), so they stay. `Couldn't open it: {exc}` (open in the OS) carries an OS error; it is the maintainer's call whether to fix it, since a user opening a file benefits from the reason.
