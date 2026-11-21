# 0056: A script's missing package is installed from the chat, after the person says yes

## Status
Proposed (2026-11-20, OICWS approved the plan in the project thread and chose that an install
behaves as one from Settings). Adds to 0021 and 0022, which it does not change. Issue #1007,
from #1002.

## Context
`run_python_script` and `run_node_script` run in coscribe's own environments (`script-env`, a
venv; `node-env`, an npm folder). A package missing there failed the script, and the tools told
the model it could not install anything: the person had to find Settings › Packages, type the
name and ask again. A background command is no way round it: in the sandbox it can't write those
folders or reach the network, and outside it each command needs the person's approval anyway.

## Decision
- **One deferred question tool, `install_package(runtime, package, reason)`**
  (`conversation/package_install.py`). Like `request_folder_access` it is answered on a card, so
  accept-edits, auto mode, the reviewer, exec policy and a workspace's `settings.json` never
  approve it. Only the person installs a package. The schema is fixed; what is installed reaches
  the model only in a tool result (0001).
- **The card** names the environment, the package and the model's reason, links its page on
  pypi.org or npmjs.com, and has Install and Not now. It then shows the install running and ends
  as the installed version or the installer's own error.
- **The same installer as Settings**, into the same environment, run as the user outside the
  AppContainer and the command sandbox, as an install from Settings is.
- **A plain name only**: a name with at most a version (`openpyxl`, `openpyxl==3.1.2`,
  `sharp@0.33.5`). A URL, a path, a git address, an option or several names are refused before
  any card.
- **No card when it is there**: a package already installed, at the version asked for if any, is
  answered with its version.
- **Not now holds** for that package in the conversation while coscribe runs.
- **No card where nobody is watching**: a scheduled or workflow run is told to name the missing
  package in its result; sub-agents don't get the tool.
- **Audited** like an approval: the package, the answer and whether the install worked.

## Consequences
- Settings › Packages stays (list, add, remove); dropping its Add is decided separately.
- A package's own install code (a pip source build, an npm install script) runs as the user, as
  from Settings. The card's link lets the person check the name first.
- After a reload the card shows as the tool row "Asked to install …", without its outcome.
