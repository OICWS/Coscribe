# The five secrets tests that asserted nothing now check what they are named for (shipped)

Why: the ratchet listed five tests in `tests/test_secrets.py` with no assertion (issue #99). A no-op or error-swallowing helper can quietly start deleting the wrong keychain entry or stop cleaning up, and such a test would still pass.

## Shipped
- The fake keyrings record what they were asked to delete (`_FakeKeyring.deleted`, `_AlwaysFailingKeyring.delete_attempts`).
- `delete_secret` with a plain string and with `None`, and `env_delete_secret_if_ref` with a plain value and `None`: each returns `None` and deletes nothing from the keyring.
- `delete_secret` with a failing keyring returns `None`. It also really attempted the delete, so its error was swallowed rather than the delete skipped.
- `harden_file_permissions` on a missing file returns `None` and does not create the file.
- Each assertion was checked against a deliberate break of `runtime/secrets.py`, restored after; the file is not part of the change. There were seven breaks:
  - a plain string treated as a keyring ref;
  - `None` treated as a ref;
  - the `KeyringError` not caught;
  - the delete skipped;
  - any `.env` value treated as a ref;
  - `chmod` errors not caught;
  - the file created.
  Each failed the test meant to catch it.
- `quality/baseline.json`: `tests_without_a_check` goes down by five (`ratchet.py --update`).

## Not verified
- The keyring paths against a real Windows Credential Manager; these tests use the fakes, as before.

## Follow-ups
- The last 6 entries of #99: `tests/test_presentations_tool.py`.
