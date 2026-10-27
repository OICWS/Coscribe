# The design-system menu E2E no longer races the menu closing (shipped)

Why: the nightly E2E of 2026-10-27 failed once on `artifacts.spec.ts` "the design-system menu leads to the page that manages them": the click on "Make a new design system first" waited out the 45 s test timeout.

## Shipped
- `chooseFromDesignMenu` clicks the item inside the retried block, so a menu that closes between being seen and being clicked is opened again instead of failing the click.

## Not verified
- The race is not reproduced on purpose; only that the spec passes in CI.
