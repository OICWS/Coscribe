# The Slides e2e specs run on a Windows runner (partly shipped)

Why: issue #472, item 1. The maintainer tests the Slides editor by hand on Windows; the specs
only ran on Linux.

## Shipped
- `windows-more-checks.yml` has a `slides-e2e` job: it starts the stub model, `coscribe-web` and
  Vite on `windows-latest` and runs `slides.spec.ts` and `slides-panels.spec.ts`. It is in this
  workflow and not in `e2e.yml` so a red Windows run does not turn the Linux E2E night red, and
  the workflow already runs on Windows for its own paths. Servers and specs share one step.
- The workflow also runs on a pull request that changes a Slides spec, the deck fixtures or the
  stub model.

## Not verified
- Green on `windows-latest`: see the PR for the run.

## Follow-ups
- The other specs are not run on Windows.
