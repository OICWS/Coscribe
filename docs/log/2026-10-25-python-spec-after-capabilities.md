# The Python interpreter spec opens the section first (shipped)

Why: the Capabilities page keeps Python and packages behind "Show Python and packages", so
`python-interpreter.spec.ts` found no "Automatic" radio and the nightly E2E on `main` went red.

## Shipped
- `tests/e2e/python-interpreter.spec.ts` clicks "Show Python and packages" before it looks for
  the list of Pythons.

## Not verified
- Only Chromium on Linux against the local stack.
