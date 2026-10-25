# Settings pages use one button-and-menu select and borderless segmented controls (shipped)

Why: the native `<select>` popup in Settings was drawn by the OS and clashed with the rest of the
page, and the segmented controls carried a dark outline.

## Shipped
- `settings/SelectMenu.tsx`: a borderless button that opens a menu with a check on the current
  item. It replaces the native selects for Default model, Code model, Archive inactive
  conversations and folder access, and replaces the segmented control for Interface font and Motion.
- `SegmentedControl` loses its border; Theme, Default mode and the others keep it.
- The folder access e2e spec drives the menu instead of `selectOption`.

## Not verified
- Windows and the Electron shell; checked in headless Chromium, light and dark.
- Keyboard arrow navigation inside the menu (Escape and click outside close it).
- The dialog-only `SecretPicker` and the workflow editors still use a native select.
