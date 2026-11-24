# Promo page: what it says matches the app again

Why: the maintainer found much of the promo page out of date. It stays in English and Chinese.

## Shipped
- Workflows: the lead names the triggers (a schedule, a file in a folder, a connector, an event
  from another program), and the first point is the autonomy choice (fixed steps, self-healing,
  fully autonomous) instead of "Built on LangGraph"; a failed check is named in the run's report.
- Models: the provider presets the app has now (Doubao, OpenRouter, LM Studio and more).
- FAQ "How is it different": rewritten from the README's list. It no longer says LibreOffice
  draws every preview (Office or WPS does; LibreOffice is optional), that a turn's steps have a
  hard limit (they have none since 2026-11-11), or a cost figure nothing in the repository
  backs; it adds artifacts and the built-in browser.
- Run from source: installs through `scripts/install_locked.py` as the README does, without the
  old `google-genai` pin.
- The product mock's sub-agent pane is named "Background tasks", as in the app, and the message
  box shows the workspace ("Default") instead of "Add folder".
- The demo's fourth scene (handing code to the code module) is replaced by two, drawn from the
  running app: **04 · WEB** asks to export renewals from a CRM; the Browser panel asks "Allow
  Coscribe to use crm.example.com?", shows "Coscribe is using the browser" with Take over while it
  fills two fields and saves the table across three pages to a CSV. **05 · DOC** writes a Doc
  (`q3-review.md`, the file card "Document · .md"), opens it in the Doc panel with its chart,
  checklist and NOTE callout, and ticks a checklist item ("Saved").

## Not verified
- The browser scene follows `DesktopBrowserPanel.tsx`; the desktop app itself was not run here
  (the web UI's panel needs a local Edge or Chrome).
- The Pages deploy itself (runs only from `main`). Looked at in Chromium on Linux, both languages.

## Follow-ups
- In the app's detailed view a browser step's row shows the raw tool name (`browser_fill_form`,
  `browser_save_table`): `lib/transcriptGrouping.ts` has no labels for them. The demo uses words
  like the task page's (`lib/plainSteps.ts`). Noted in `docs/plan.md`.
