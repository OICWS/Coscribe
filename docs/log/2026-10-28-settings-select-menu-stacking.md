# An open settings dropdown no longer sits under the rows below it (shipped)

Why: the "What best describes your work?" menu opened underneath the Theme, Interface font and
Motion controls, which showed through it.

## Shipped
- `SettingRow` gives its own row `z-10` while a control inside it is expanded. Each row is
  `isolate` (for the search-flash highlight), so a menu's own `z-20` only counted inside its row and
  later rows painted over it.

## Not verified
- Not seen in a running app here; checked by reading the stacking rules only.

## Follow-ups
- none
