# Property tests for secret redaction and the workspace guard (shipped)

Why: two promises are about any input, so example tests cannot show them: a stored
secret's value never survives redaction in any form the code claims to cover
(decision 0003), and a path `WorkspaceScope.resolve` accepts never lies outside the
allowed folders. Part of #105, closes #109.

## Shipped
- `hypothesis>=6.169.0` in the dev dependencies.
- `tests/test_secret_redaction_properties.py`: every form `_forms` documents (as is, URL-encoded
  both ways, hex both cases, JSON-escaped, base64 standard and URL-safe, padded or not) is gone
  from `redactor(...)(text)` at the start, middle, end, repeated and beside other secrets; a text
  with no secret is unchanged; `redact_secrets` blanks known token formats at any depth, blanks the
  whole value under a secret-named key, keeps the shape and leaves other content equal.
  The forms are listed again in the test from the docstring, not read from the code.
- `tests/test_workspace_properties.py`: generated paths (`..`, `.`, empty segments, `/` and `\`,
  absolute, drive-letter, UNC, `~`, a sibling folder sharing the root's name as a prefix, a symlink
  out) are refused or resolve inside the allowed folders; read and write scopes differ.
- All with `deadline=None`, `derandomize=True`; the whole pair runs in about 5 seconds.

## Not verified
- Windows. On Linux a backslash and `C:` are ordinary file-name characters, so those paths resolve
  inside the root; on Windows they are separators and a drive. The property is written to hold on
  both, but only Linux was run here; the nightly Windows job runs the other.
- The symlink test skips where the platform refuses to create a symlink.

## Follow-ups
- #115 (nightly mutation testing) builds on these.
