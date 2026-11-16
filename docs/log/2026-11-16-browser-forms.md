# One step fills a whole form, does several things on a page, or waits for one of several texts (shipped, part 2a of #915)

Why: a form with a dropdown, a checkbox and a date took one step per field, a page change that
went wrong in a form showed only later, and a submit that can end in success or an error could
only wait for one of them. The maintainer asked for these in conversations and saved workflows
alike (#915).

## Shipped
- `browser_fill_form` fills every field kind in one call: text is typed as before, a native
  dropdown chooses the option, a checkbox takes "checked" or "unchecked" (other words are refused),
  a radio button is chosen, a date or time field gets its fixed format through the value setter
  (Chromium's pickers take no typed text). Each field is read back; the result names any value
  the page changed (upper-cased, reformatted), the rest stay quiet (`browserAgentForms.ts`, which
  also holds the steps and the wait; its page function `pageFields` reads pageAgent's refs).
- `browser_steps` runs several actions on one page in order (`fill`, `type`, `select`, `click`,
  `press_key`, `wait_for`), stopping at the first that fails with which step it was and what was
  done before it. The steps are checked before the page is touched.
- `browser_wait_for(any_of=[...])` ends at the first of several texts; the result's `found` is a
  value a saved workflow's next step can branch on.
- Self-healing (decision 0030) may use `browser_fill_form` and `browser_steps`, held to the same
  rule as a typed field: only values the run has, and only plain keys. The step list says
  "Fills in 3 fields", "Does 2 things on the page", "Waits for the page to show “Saved” or “Error”".
- The form tools move to `tools/web/_browser_forms.py`; the wait limits to `_browser_pages.py`.
- Tests: `scripts/browser-native.cjs` (real Electron) fills a dropdown, a checkbox, a radio, a date
  and a field the page upper-cases in one call and checks the read-back, refuses an unclear
  checkbox word, runs steps that end in a wait, stops at a missing element with what was done, and
  waits for one of two texts; pytest covers the tools' arguments and output and a heal that tries
  a guessed value in a form fill and in steps.

## Not verified
- A person using the Windows app, and custom (non-native) dropdowns: those are still clicked
  open and chosen with `browser_click`.

## Follow-ups
- Part 2b of #915: drag and drop, copy and paste (a design note on the clipboard first).
