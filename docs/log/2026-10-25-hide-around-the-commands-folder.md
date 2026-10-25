# A private folder that holds a command's folder hides what is beside it, not itself (shipped)

Why: the real-Windows run of the code module's commands (#617) showed PowerShell starting in
`C:\` instead of the task folder when that folder lay inside a hidden one (AppData there; the
Desktop or Documents for a person). Its user can't list the parents, so a relative write failed.
The maintainer chose to hide what is beside the way down instead of the whole folder.

## Shipped
- `hidden_around` in `tools/exec/_private_folders.py`: a private folder holding the command's
  folder gives way to every entry beside the way down to it; `sandboxed_command` applies it. A
  deny Codex left on a folder on that way is taken off, as for a folder given to the environment.
- Decision 0022 says so, with the names of those entries now listable.
- Real-Windows test: PowerShell 7 and Windows PowerShell start in a workspace in Documents, and a
  file beside it in Documents stays hidden.

## Not verified
- A Desktop or Documents with very many entries: each becomes one deny entry in the profile.
