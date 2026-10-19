# The structure period against record 0009 (2026-10-19)

Record 0009 (accepted 2026-10-11) set no numeric exit criteria of its own; this report takes each of its commitments and the numbers from the assessment it cites (`docs/assessments/2026-10-11-scale-to-1m-lines.md`) and says where each stands on 2026-10-19 (main at 054337d).

## The numbers, at the start and now

| What | 2026-10-11 | 2026-10-19 | Where it is kept |
|---|---|---|---|
| Cross-package imports into a submodule (`deep_imports`) | 165 of 205 | 2 in the baseline (exit criterion 40 or fewer, met) | `office-agent/quality/baseline.json`, `ratchet.py` |
| Stale references to deleted files | 126 | 0 | `tests/test_doc_references.py` |
| Files over 1,000 lines | 7 | 7 in the baseline (`file_lines`; `presentations.py` is an 83-line entry point, `session.py` 1,472) | ratchet |
| Functions over 100 lines | 39 | 34 | ratchet (`long_functions`) |
| Functions with complexity over the limit | 33 over 20 | 18 | ratchet (`complex_functions`) |
| Tests without an assertion, `monkeypatch` by string | 15 and 42 | 0 and 0 | ratchet |
| Mutation score of `runtime/secret_store.py` | 68% (297 of 444) | 96% (425 of 444; the 19 left are equivalent) | `docs/log/2026-10-14-mutation-secret-store.md` |
| Coverage | not measured | measured in CI, floor 88 | `pyproject.toml` |
| Reviews on record | 0 of 66 PRs | reviews are GitHub reviews; the PR template asks for the link | decision 0006, PR template |
| Slice for a small change | about 210k tokens for a PowerPoint change | 5 to 9 files, 4.5k to 5.6k tokens read in three fresh-session samples (budget 15 files, 150k) | `docs/metrics/2026-10-17-fresh-session-slice.md` |
| Size | 49.6k Python source lines, 36.5k test lines | 97.1k source, 53.2k test; frontend 36.1k | `find` on `main` |

The core stays near the roughly 100k-line budget (97.1k source lines, vendored code included).

## Batch 10 (#425)
Done: 1 (workbook cell notes), 3 (the ratchet is enforced and a test keeps it wired), 4 (workflow spec below `tools`; the layers contract ignores nothing), 6 (the inventory found no product call), 8 (a Playwright spec for the Slides panel, nightly in `e2e.yml`), 9 (a property test for arranging and undo), 10 (the editor's source functions in jsdom, judged by the server's parser), 2 (the first Audit finding was the runner's setuptools, fixed in #453; the Word review routes return fixed messages for the library's and the OS's errors, #454). Closed with a reason: 5.

## What stays open, and where it is tracked
- The Windows nightly must be green 14 scheduled nights before it is required: 1 of 14 on 2026-10-19 after the red nights of 10-16, 10-17 and 10-18 (#232, `docs/plan.md`).
- 20 checks that need a person on Windows or with an account (`docs/metrics/2026-10-17-not-verified-triage.md`).
- Maintainer settings: Dependabot security updates, secret scanning and push protection (#263).
- CodeQL alerts: not read here, because the integration used by this session can list checks but not code-scanning alerts. The CodeQL check passes on every PR since it was added. The maintainer reads the alerts page (#425 item 2).
- `Couldn't open it: {exc}` in the open-in-OS route still returns the OS's text; the maintainer's call (`docs/log/2026-10-19-review-error-text.md`).
- A frontend card, and the second reviewer for invariant paths (Codex), which waits for the second maintainer.
- `Gemini effort` (#315, probably superseded) and the deck-notes review request (#250).
- Lifting the period is the maintainer's: 0009 says only he lifts it.

## Not verified
- The 14-night count is the scheduled runs of `windows.yml`; the manual runs of 10-19 do not count.
- The 2026-10-11 figures are the assessment's; the current ones come from the baseline files and the commands in the table, not from a fresh run of `ratchet.py` here.
