# Stabilize changed-function mutation checks

Mutmut runs tests in a scratch tree and can reorder them. Its placeholder page now has
the head element needed by the launch-token integration test. The tool-deferral approval
test uses its own tool, and the proxy test restores the runner's environment for later
package installs. Protocol declarations without an implementation are left out of the
mutation targets. Mutmut exit failures now appear in the report with their error output.

PR mutation jobs run one selected module per runner after both PRs hit the
serial job's 40-minute limit. The workflow also publishes a combined table.
