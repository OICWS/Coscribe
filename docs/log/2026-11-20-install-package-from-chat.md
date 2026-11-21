# A script's missing package is installed from the chat (shipped)

Why: a script that needed a package missing from script-env or node-env failed, and the person
had to add it in Settings › Packages and ask again (#1002, #1007). Decision
[0057](../decisions/0057-a-scripts-missing-package-is-installed-from-the-chat.md).

## Shipped
- `install_package(runtime, package, reason)`, a deferred question tool
  (`tools/bookkeeping/interaction.py`), answered in `conversation/package_install.py`: a plain
  name with at most one version, an already-installed package answered without a card, Not now
  held for the conversation, the install through Settings' own installer, an audit entry.
- Two socket events, `package_install_required` and `package_install_finished`
  (`conversation/wire.py`), and the card (`frontend/src/components/chatlog/PackageInstallCard.tsx`):
  waiting, installing, installed, failed with the installer's output under Details, not installed.
- `run_python_script`, `run_node_script` and `run_background_script` now point the model at the
  tool instead of Settings.
- Tested live on Linux against the stub model: real installs of `humanize` (pip) and
  `dayjs@1.11.13` (npm), a failed one, and Not now.

## Not verified
- A real Windows machine; a real model choosing the tool after a `ModuleNotFoundError`.

## Follow-ups
- Drop Settings › Packages' Add field once this has been used for a while (`docs/plan.md`).
