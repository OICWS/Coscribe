# Settings polish: Python and packages in dialogs, wider rows, instructions limit (shipped)

Why: issue #1002 and its comments listed small problems in Settings: the Python picker felt
unresponsive and wrapped badly, a path field instead of a file picker, Advanced rows expanding
inline, the workspace dialog sitting high in the desktop app, rows wrapping early, Global
instructions with no limit and its own "Saved", and a menu arrow on the empty New session screen.

## Shipped
- Settings › Capabilities › Advanced: **Choose** and **Manage** open dialogs (`SettingsDialog.tsx`,
  laid out like the workspace dialog). The Python dialog shows "Searching for Python…" at once,
  its download row reflows, and another Python is picked with the system file picker
  (`dialog:pick-file` in `office-agent-desktop`); a browser tab keeps the typed path.
- `SettingRow`: the text column takes the width up to the control instead of stopping at 480 px.
- Dialogs (workspace, Allowed folders, the new ones) are centred below the desktop title bar
  (`DIALOG_BACKDROP_CLASS` in `lib/titleBar.ts`), as Settings itself is.
- Global instructions: a live count against 2,000 characters; text over it is kept, not saved
  and not cut, until it is shortened; a save shows the Settings window's own "Saved".
- The toolbar's menu arrow is hidden on the empty New session page only.

## Not verified
- On Windows: the native file picker, and the dialog position under the real title bar (checked
  in a browser with the desktop bridge stubbed).
