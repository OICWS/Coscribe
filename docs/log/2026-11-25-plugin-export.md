# Export a plugin or a skill as a .zip (shipped)

Why: step 7 of #1036 (decision 0058): a plugin made or changed in Coscribe can be kept or shared,
and Upload takes it back.

## Shipped
- `GET /api/skills/{name}/export` (`?plugin=true` for a plugin): the folder as a .zip holding that
  one folder. Links, `__pycache__` and Coscribe's source note are left out, so nothing outside the
  folder goes with it. Built-in plugins export too.
- Settings › Plugins: **Export as .zip** in the ⋮ menu of a plugin, its page and a skill.
- Checked in the app: exporting a plugin from the menu saved `notes-kit.zip` with its three files.

## Not verified
- On Windows; the desktop app's save dialog for the download.

## Follow-ups
- PPTX Pages exported with a converter that runs outside Coscribe: decided as its own item
  (2026-11-25), since the deck engine's build imports most of `coscribe.tools`.
