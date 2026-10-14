# Mutation survivors of `runtime/secret_store.py` killed or explained (shipped)

Why: the nightly mutation run left 135 survivors, 12 of them in code no test reached (#221, part of #165).

## Shipped
- `tests/test_secret_store.py`: the exact refusal messages of `save`, `clean_hosts`, `resolve` and `SessionEnvironments.set`; the limits at their edges (20 hosts, 16,384-character value, 100 variables, 4,096-character variable value); the keys and defaults of `entries`, `hosts_of` and `save`'s return value, and `created_at` kept across saves and written in UTC; the exact file content and nested state folder; files always read and written as UTF-8 and non-ASCII variables kept as written; `delete` and `detach_everywhere` (unreadable and non-map files skipped without stopping); `placeholders_in` and `substitute`; and the redaction: every encoding of a value, the longer of two overlapping values first, the cache reused until `secrets.json` changes, and one unreadable secret not stopping the others.
- `python scripts/mutation.py run secret_store --out DIR` (mutmut 3.8.0, Linux): before, 297 of 444 caught (the numbers in #221); after, `{"mutants": 444, "killed": 425, "survived": 19, "timeout": 0, "no_tests": 0}`. The 19 left are all equivalent, below. No change under `src/`.

| Group | Mutants | Why the behaviour cannot differ |
|---|---|---|
| `"utf-8"` to `"UTF-8"` or `"ASCII"` (`_read`, `_write`, `get`, `set`, `detach_everywhere` x2, `_forms` x2) | 8 | Python's codec names are case-insensitive; the `ascii` decode only sees base64 text. |
| `".tmp"` to `".TMP"` (`_write`, `set`, `detach_everywhere`) | 3 | The temp file is renamed away before anything looks at it. |
| `ensure_ascii` omitted, `True` or `None` in `secrets.json` (`_write` x3) | 3 | Everything in that file is ASCII: names, `secret:NAME` references and ISO timestamps match ASCII-only patterns, and a host name must too (the host pattern allows `a-z`, `0-9` and `-`, so an internationalised name has to be given as punycode; a test refuses `例え.jp`). |
| `ensure_ascii=None` in the session files (`set`, `detach_everywhere`) | 2 | `None` is falsy, the same as `False`. |
| `host != pattern[2:]` to `[3:]` (`host_allowed`) | 1 | `endswith(".example.com")` already excludes `example.com`, so the second test is never decisive. |
| `raw = {}` to `raw = None` (`SessionEnvironments.get`) | 1 | The next line turns any non-dict into `{}`. |
| `quote(value, safe="")` to `safe="XXXX"` (`_forms`) | 1 | `X` is always left unquoted, so the output is the same. |

## Not verified
- Windows: mutmut forks and runs on Linux only; the tests are plain unit tests. The UTF-8 test checks the `encoding` argument, since this Linux run cannot show a locale difference.

## Follow-ups
- #165 closes with the per-module numbers once the other mutation issues are done.
