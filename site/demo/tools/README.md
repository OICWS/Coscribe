# The homepage demo

`site/demo/` replays ten real Coscribe conversations (five tasks, in English and Chinese) in the
app's own markup and stylesheet. `site/index.html` embeds it and picks the task and language.

Nothing in a scene is drawn by hand. Each `scenes/<lang>-<n>/scene.json` is what the real UI drew
when it was given the exported conversation:

1. The runs: each task ran in the Windows desktop app (deepseek-flash, effort Low, Auto mode) on
   sample files with made-up data. Each run's export holds `socket-events.json` (the `state` and
   `history` events the UI receives), its input and output files, and `run.json`.
2. `bash build.sh` (after `npm run build` in `office-agent/frontend`) copies the app's built
   `style.css` to `app.css`, its fonts to `fonts/`, and bundles the app's tool-call wording
   (`transcriptGrouping.ts`) into `labels.js`.
3. `capture.cjs` opens a running `coscribe-web` in Playwright, posing as the desktop shell so the
   window has its desktop title bar, answers the conversation's socket with the exported events,
   and saves the window, prompt, replies, each call's opened view, the made-file notice and card,
   the panel the file opens in (slides are fetched from the server as SVG into `media/`), the
   running composer and, for a run that used the browser, the Browser panel asking for the site
   and in use:

   ```bash
   # the run's input and output files in the server's workspace first; REAL is any thread id
   node capture.cjs <export>/<lang>/<scene> ../scenes/<lang>-<n> <REAL> [http://127.0.0.1:8000]
   ```

   `DEMO_SHOTS=<folder>` also saves screenshots to compare against the Windows frames.

What the demo changes, and why:

- `overrides.json`: two English runs answered partly in Chinese and Spanish; those replies are
  the same words in English.
- Money such as `$13,375,000` is escaped before the capture, because the app's Markdown reads two
  dollar amounts as a formula (a bug, in `docs/plan.md`).
- `demo.js` words a few tools the app still shows by their raw name (`build_pptx_from_pages`,
  `browser_snapshot`), and fills in what the capture can't know: each conversation's title and
  how long the run took on Windows, which the turn timer counts through in fast forward.
- `crm/` is the sample site the web task used, live in the Browser panel; the demo sets its
  filter and page as the run did.
