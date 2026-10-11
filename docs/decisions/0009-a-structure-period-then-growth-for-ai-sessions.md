# 0009: A structure period, so AI sessions can keep up with growth to 1M lines

Status: accepted (2026-10-11).

## Context
The goal is a codebase of about 1,000,000 lines that AI sessions develop,
refactor and review, with humans merging, while no session can read more than a
sliver (about 1M tokens of context against about 11M tokens at that size). An
independent assessment (`docs/assessments/2026-10-11-scale-to-1m-lines.md`)
measured today's gap: packages have no public interface (165 of 205
cross-package imports reach into a submodule), nothing fails when documents go
stale (126 references to deleted files), reviews and "not verified" items leave
no record, and mutation testing of `runtime/secret_store.py` scores 68% at 95%
coverage.

## Decision
- **Features pause for a structure period of 2 to 3 weeks** from 2026-10-11:
  only bug fixes and fixes found while verifying. The maintainer lifts it.
- **Numbers are ratchets**: coverage, size and complexity budgets, public
  interfaces, tool-schema snapshots. A baseline can only improve; the baseline
  files are under `CODEOWNERS`, and **only a human may loosen one**.
- **Invariant paths get a second reviewer from another model family** (Codex), and
  reviews are posted as GitHub reviews so they leave a record.
- **A change should need a bounded slice** (target: about 15 files, about 150k
  tokens), through packages with a public interface and a short card each.
- **The core is budgeted at about 100k lines**, as the assessment defines it.
- **Human minimum**: about 2 hours a week of smoke testing on a real Windows
  machine, approving decision records and any loosening of a baseline, and a
  security review each quarter. The second maintainer joins this when they arrive.
- **Not decided**: moving the repository to a GitHub organisation (merge queue and
  team code owners need one).

## Consequences
- `docs/plan.md` lists the ordered steps; the first five are tooling and records,
  not product changes.
- Large splits (`presentations.py`, `conversation/session.py`) wait for the
  golden-file and approval tests the steps before them add.
- 0007 is accepted with this: code-owner review extends to the baselines,
  snapshots and import contracts.
