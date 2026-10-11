## What and why

<!-- What changes, and the reason. Link the issue if there is one. -->

## Issue

<!-- `Closes #N` or `Part of #N`. Needed when the change is over about 200 lines, touches a hot file (see office-agent/CLAUDE.md) or an invariant path. Otherwise write `none: <why>`. -->

## Area

<!-- runtime / tools / server / code module / frontend / desktop / docs: one area per PR -->

## How it was checked

- [ ] `cd office-agent && bash scripts/check.sh` passes, or CI is green (frontend `tsc -b` and build, oxlint, ruff, mypy, pytest)
- [ ] A test fails without this change (or: why none is possible)
- [ ] A UI change was looked at in the running app (screenshot below)
- [ ] `docs/log/<date>-<slug>.md` records what shipped (and `docs/plan.md` is updated if the open work changed)

## Independent review

<!-- Only if the change touches an invariant path (office-agent/CLAUDE.md): the link to the GitHub review a separate session posted with `/code-review <PR> --comment`. Otherwise: not needed. -->

## Not verified

<!-- What you could not test (a real account, a platform, a vendor flow). Say so plainly, and say if a script could check it on Windows. -->

## Screenshots

<!-- UI changes only -->
