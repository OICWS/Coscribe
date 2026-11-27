# Stabilize changed-function mutation checks

Mutmut runs tests in a scratch tree and can reorder them. Its placeholder page now has
the head element needed by the launch-token integration test. The tool-deferral approval
test uses its own tool. Pytest restores the process environment after each test so proxy
settings and connector paths cannot leak into reordered tests. Protocol declarations without an implementation are left out of the
mutation targets. Mutmut exit failures now appear in the report with their error output.

PR mutation jobs run one selected module per runner after both PRs hit the
serial job's 40-minute limit. The workflow also publishes a combined table.

The replay model test releases its tape and uses a private context so the
next replay can still find its own tape from a background task.

The slow-tool regressions give the fake model time to answer on a busy Windows
runner. Their tools still take longer than the model stall limit.

The changed-function selector compares the executable code before and after the PR.
A type-only edit to an instance attribute in a function skips mutation of that
unchanged function. This removes the session constructor from the run while retaining
the three conversation methods whose behavior changed.
