# The rename and confirm dialogs are dialogs to assistive technology, and the Artifacts spec clicks as a person does (shipped)

Why: `artifacts.spec.ts` "a card's menu renames, copies and deletes" sometimes found no Delete item
after a rename (#511). The spec waited for `getByRole("dialog")` to be hidden, but `RenameDialog`
had no dialog role, so the wait passed at once while the rename was still in flight. The forced
click on the card's menu button then landed on the dialog's backdrop, whose click is Cancel, and no
menu opened. Locally, one forced click right after the rename failed 20 times out of 20; the spec's
retry loop hid that.

## Shipped
- `components/artifacts/RenameDialog.tsx` and `components/ConfirmDialog.tsx`: `role="dialog"`,
  `aria-modal` and the title as the dialog's name, so a screen reader announces them and a spec can
  wait for them.
- `tests/e2e/artifacts.spec.ts`: `openOptions` hovers the card and clicks its menu button without
  `force` (the click waits until nothing covers the button), then checks the menu is open. The
  retry loops around those clicks are gone; the rename waits for the "Rename" dialog to close.
  `getByLabel("Name")` is exact, since the dialog's own name "Rename" contains it.
- Checked locally against the stub model: the spec 10 times over, 100 of 100 passed.

## Not verified
- A screen reader on Windows reading the two dialogs.
