# The model menu opens over the save offer (shipped)

Why: with the "Save this job?" notice showing, opening the model picker put the notice's
"Save as workflow" and close buttons over the menu, hiding the second model (#1109).

## Shipped

- The model menu (`ModelPicker.tsx`) stacks at `z-20`, like the composer's other menus
  (`ModePill`, `EffortPicker`, `EnvironmentPicker`); the notice buttons sit at `z-10`.
- `tests/e2e/model-picker.spec.ts` opens the menu over a save offer and checks that nothing
  covers any of its rows; it fails without the change.

## Screenshots

- [Before](screenshots/model-picker-over-notices-before.png)
- [After](screenshots/model-picker-over-notices-after.png)

## Not verified

- The desktop app on Windows; Chromium on Linux showed the overlap and the fix.
