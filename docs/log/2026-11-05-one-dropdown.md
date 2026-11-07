# Every dropdown of the app is the Settings menu, not the native select (shipped)

Why: the scheduled-task form (Frequency, Permissions, Model) and the workflow step editor
(Try again and the rest) still used the native `<select>`, whose popup Windows draws in its own
blue-highlight style and font. Settings already had the app's own menu; the maintainer asked for
one look everywhere.

## Shipped
- `components/SelectMenu.tsx` (moved out of `settings/`, it is shared now): a `field` variant,
  bordered like the inputs beside it, next to the borderless `plain` one of a settings row;
  disabled options, group headings (in place of `<optgroup>`), number values, `id` for a
  `<label htmlFor>`, `invalid` and `disabled`.
- The menu opens in a portal fixed to the viewport, above the trigger when there is more room
  there, so a dialog or the step sheet can't clip it; it follows the trigger on scroll. Keyboard:
  the arrows open it and move through the options, Home and End, Escape closes it without closing
  the dialog under it.
- All 34 native selects in 19 files replaced: the scheduled-task form and its schedule fields,
  the step editors (failure, pause, condition, agent, run a task, memory, loop, tool arguments,
  output fields), inputs and remembered values, the quick-edit sheet, the autonomy choice, the
  run view's model, Settings' secret picker and design-system asset kind. None is left in `src/`.
- The e2e specs that used `selectOption` pick through `pickOption` in `tests/e2e/helpers.ts`.

## Not verified
- On Windows in the Electron window: the menu was checked in Chromium on Linux (light and dark),
  not in the desktop app.

## Follow-ups
- None.
