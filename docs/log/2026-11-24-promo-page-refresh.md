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
- The hero's demo is no longer a hand-built recreation of the app: the maintainer found it did not
  match the real one. It now steps through real screenshots (`site/media/demo/{en,zh}/`), three
  or four per scene, taken from the desktop app built from `main` on the maintainer's Windows
  machine, running each scene's request with deepseek-flash on sample files with made-up data.
  The tabs, step buttons, a click on the picture and the play button move through them; captions
  say only what the frame shows. **04 · WEB** asks for a small sample CRM served on the same
  computer, so its request names that address; the app asked to use the site first, and the
  maintainer allowed it. Both decks have 8 slides, and both reviewed contracts hold tracked
  changes and comments (checked in the files).

## Not verified
- Opening a .docx output card did not open a panel in the desktop app, so the contract scene ends
  on the reply and its file card.
- The Pages deploy itself (runs only from `main`). The page was looked at in Edge on Windows,
  both languages, at desktop and phone width.

## Follow-ups
- Things the real runs showed, also in `docs/plan.md`: dollar amounts in a reply are drawn as
  maths (`$13,375,000 revenue, $4,798,139` becomes italic run-together text); a .docx output card
  opened no panel; the English web run answered partly in Chinese.
- In the app's detailed view a browser step's row shows the raw tool name (`browser_fill_form`,
  `browser_save_table`): `lib/transcriptGrouping.ts` has no labels for them. The demo uses words
  like the task page's (`lib/plainSteps.ts`). Noted in `docs/plan.md`.
