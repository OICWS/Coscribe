# Scripts' Python: found on the computer and chosen, downloaded only on request (shipped)

Why: since #583 the first script on Windows downloaded coscribe's own Python from GitHub and the
baseline packages from PyPI without asking, and failed where GitHub is blocked. Allen's call
(#586): search the computer, let the person choose, keep the download but only on a click.

## Shipped
- `tools/exec/find_python.py`: the Pythons offered in Settings > Environment, from the PEP 514
  registry entries, `py -0p`, PATH and the usual folders (per-user and Program Files installs,
  `C:\Python3*`, uv, Anaconda/Miniconda). Each is run with `--version`; Python 2, the WindowsApps
  aliases and the same file under two names are left out.
- `script_env.py`: a script venv is never made by downloading Python. Order: the chosen one,
  coscribe's own if already downloaded, then the ones found. A failed package install removes the
  venv, so the next run does not take a venv without its packages.
- `POST /api/script-env/own-python` downloads coscribe's own Python (about 30 MB) and chooses it;
  the picker offers it only where a build exists (Windows).
- Choosing a Python sets up the environment and runs the isolation check at once
  (`isolation_status(run=True)` makes the venv when there is none, `setup_failed` when it can't).
  The check's cache now keys on the installation the venv was made from as well.
- From Python 3.13 on, the "Failed to find real location" line Python prints in the container is
  dropped from a script's stderr (`isolation.quiet_stderr`).
- Edit environment > Scripts says when scripts have no Python yet and where to choose one.

## Not verified
- On Windows: the registry and `py -0p` search, and choosing a Python then running the check, run
  only in CI's unit tests here; nobody clicked through it on a Windows machine.
- The package list under the picker is not reloaded after choosing another Python; it shows the
  new venv's packages when Settings is opened again.

## Follow-ups
- A PyPI mirror setting, for networks where PyPI is slow or blocked.
