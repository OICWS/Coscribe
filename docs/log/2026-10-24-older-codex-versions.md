# An older Codex left by a version bump is cleared, or can be removed (shipped)

Why: each Codex version installs in its own folder (`codex/<version>`). After the pin moved to
0.163.0, Settings showed only "Download now" for the new version. The 0.160.0 folder stayed on
disk, and nothing listed it or offered to remove it.

## Shipped
- Once the pinned version is downloaded, the older version folders are deleted. The one the
  command sandbox was set up with is kept, because deleting it would turn the sandbox off
  (`code_runtime/install.py`: `older_versions`, `remove_older_versions`).
- The code status lists the older versions still on disk (`older`). Settings shows them with
  their size, and with a Remove button while the current version isn't downloaded. It says when
  removing would turn the command sandbox off.
- Remove now deletes every version. Codex's own home, with its threads, stays.

## Not verified
- On Windows, a running older `codex.exe` keeps its folder from being deleted. That folder stays
  listed and can be removed again later. This was not tried on a real machine.
