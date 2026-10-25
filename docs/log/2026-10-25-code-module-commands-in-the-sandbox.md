# The code module's commands run in the command sandbox (shipped)

Why: Codex ran as `danger-full-access`, so coscribe refused every command it asked for, and it
couldn't run the code or tests it wrote (issue #616, step 4b of #588).

## Shipped
- Where the full sandbox is set up and commands are allowed, a code task's Codex thread starts
  under a permission profile for its folder (`code_command_profile`, made as a command's profile
  is: the environment's network, private folders hidden or not) with approval policy "never".
  Codex asks nothing; its commands and file changes run held to the folder, and it is told it
  can run its code and tests.
- Its commands are approved once per task, as a `run_code_command`, the way
  `run_background_command` is (`conversation/approvals.py`): by the person whenever the
  environment's network is Full, in every mode; otherwise by the mode and Settings › Code.
  Declined, the task runs with commands off.
- Why "never" (the maintainer's choice): the real-Windows run showed that an approved request to
  escalate makes Codex 0.163 grant the sandbox's group write on `C:\` and run the command with
  the whole disk writable, and the approval request doesn't say it is one. Under "never" Codex
  refuses the request itself. Anything it still asks is declined (`code_runtime/thread.py`).
- The code module's Codex keeps its home in the sandbox's once the sandbox is set up. That is
  where the sandbox users' passwords are, and a second setup would replace them. Its
  config.toml is the code module's settings followed by the profiles (`write_codex_config`).
- A private folder holding the task folder hides what is beside it (#619), so PowerShell starts
  in the task folder.
- Without the full sandbox nothing changes: Codex's commands are refused.
- `test_windows_real.py` runs the code module's real Codex against a stub model on the runner:
  - A command writes the task's folder.
  - PowerShell starts in a task folder in Documents.
  - A write outside it is refused, a request to escalate is refused by Codex, and nothing is asked.
  - A command runs as the sandbox's user.

## Not verified
- A real model driving Codex: the runner uses a stub Responses API.
- Codex threads made before this keep their history in the old home; a follow-up to one starts
  a new thread with the earlier report, as for a lost thread.
