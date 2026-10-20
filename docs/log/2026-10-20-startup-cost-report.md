# Startup and idle cost of the server, measured (shipped)

Why: #478. Nobody had numbers for the time from launch to the first request or for the memory
the server holds when idle, so the lazy-import and earlier-sidecar changes had nothing to be
justified by.

## Shipped
- `office-agent/scripts/measure_startup.py`: cold start to the first `GET /`, idle RSS after a
  minute, and the slowest imports by library; works on the dev server and on the packaged sidecar.
- `docs/metrics/2026-10-20-startup-cost.md`: dev server 1.86 s and 133 MiB, sidecar 1.99 s and
  142 MiB (Linux, five runs). The Office libraries are ~0.2 s of the import and ~25 MiB of the
  memory: worth moving (part 1), not a large share.

## Not verified
- Windows, a cold file cache and the installed Electron app. No Windows runner ran the script.

## Follow-ups
- Part 1 (lazy Office imports plus an import budget in the ratchet) and part 2 (sidecar earlier)
  of #478; in `docs/plan.md`.
