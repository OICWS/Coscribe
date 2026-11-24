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
- The product mock's sub-agent pane is named "Background tasks", as in the app.

## Not verified
- The Pages deploy itself (runs only from `main`). Looked at in Chromium on Linux, both languages.
