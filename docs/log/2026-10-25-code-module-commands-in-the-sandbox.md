# The code module's commands run in the command sandbox (shipped)

Why: Codex ran as `danger-full-access`, so coscribe refused every command it asked for, and it
couldn't run the code or tests it wrote (issue #616, step 4b of #588).

## Shipped
- Where the sandbox is set up and commands are allowed, a code task's Codex thread starts under a
  permission profile for its folder (`code_command_profile`, made as a command's profile is:
  the environment's network, private folders hidden or not), and Codex is told it can run its
  code and tests.
- Each Codex command is approved as `run_background_command` is (`conversation/approvals.py`):
  - The person decides when the environment has network or the sandbox is the basic one.
  - Otherwise the approval follows the mode and Settings › Code.
- A second ask for the same command (Codex's "retry without sandbox?"), a request for more
  permissions and a network host are declined without a card (`code_runtime/thread.py`).
- The code module's Codex keeps its home in the sandbox's once the sandbox is set up. That is
  where the sandbox users' passwords are, and a second setup would replace them. Its
  config.toml is the code module's settings followed by the profiles (`write_codex_config`).
- Without the sandbox nothing changes: Codex's commands are refused.
- `test_windows_real.py` runs the code module's real Codex against a stub model on the runner:
  - A command writes the task's folder.
  - A write outside it is refused and not retried outside the sandbox.
  - A command runs as the sandbox's user.

## Not verified
- A real model driving Codex: the runner uses a stub Responses API.
- Codex threads made before this keep their history in the old home; a follow-up to one starts
  a new thread with the earlier report, as for a lost thread.
