# Settings search finds individual settings and points at them (shipped)

Why: the Settings search box only matched the section names, so a person who knew a
setting's name ("Log level", "Motion") still had to guess which section held it.

## Shipped
- The search shows a dropdown: sections that match, then each matching setting under its
  section, with the typed letters in blue. Arrow keys, Enter and Escape work; Escape closes the
  list before it closes the dialog. The sidebar no longer filters.
- Picking a setting opens its section, scrolls the row to the middle smoothly, draws a
  hand-drawn wavy underline under its name (0.35 s, left to right), lights the row orange, holds
  about a second and fades back (`flashSetting.ts`, `.setting-row` rules in `index.css`).
  Settings > General > Motion: Reduced keeps the lit row and the line but draws nothing.
- `searchIndex.ts` lists the searchable rows (a tab only mounts while open, so the page can't
  be read for them); each `SettingRow` carries `data-setting-label`, which is how the row is
  found. Light and dark have their own orange.

## Not verified
- Windows and the desktop shell: checked only in Chromium on Linux against a live `coscribe-web`.
- Rows that appear only on the desktop app (Keep running in the background, notifications)
  are in the index; on the web they are absent, so picking one opens the section and does nothing more.

## Follow-ups
- A new `SettingRow` has to be added to `searchIndex.ts` by hand to be found; a test that
  compares the two would catch a forgotten one.
