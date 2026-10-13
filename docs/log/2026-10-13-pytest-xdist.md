# pytest runs on 4 workers (shipped)

Why: CI's `test` job spent about 12 minutes on pytest because it used one of the runner's 4 CPUs (issue #114, part of #105).

## Shipped
- `pytest-xdist>=3.8.0` in the dev dependencies.
- `scripts/check.sh` runs `pytest -n 4`, with and without coverage; the coverage floor check still runs.
- The Windows nightly job still calls pytest directly and stays serial.
- Evidence before switching, all on Python 3.11 with 4 CPUs and coverage on: 7 parallel runs (5 with `--dist load`, 2 with `--dist loadfile`) each passed all 2060 tests, in 4 min 0 s to 5 min 3 s. One serial run took 12 min 47 s. Coverage: 89.52% serial, 89.52% to 89.54% parallel.
- No test needed a fix: none of the 7 runs showed a failure that serial runs do not.

## Not verified
- Windows with `-n 4` (the Windows job is serial on purpose).
- Only 7 parallel runs: a rarely colliding shared resource could still exist.

## Follow-ups
- #176: audit test isolation under xdist (the `_free_port()` close-then-rebind pattern in five test files, shared `.hypothesis` and `/tmp` paths) and run `-n 4` once on the Windows job.
