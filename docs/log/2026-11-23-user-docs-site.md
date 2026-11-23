# User docs on the website: the frame and every page in English and Chinese (partly shipped)

Why: the maintainer found the app hard going for office users as it grows, and asked for a docs
site next to the existing promo page, laid out like GitHub Docs.

## Shipped
- `site/_docs/`: Markdown pages, `nav.toml` for the sidebar and `build.py`, which writes
  `site/docs/`, sized and spaced like GitHub Docs (measured on its article pages: a 740px text
  column at 16px/1.6, 325px side columns, rules between sections), with a sidebar, breadcrumbs, "本页内容" with the current section highlighted, a
  search over every page (press `/`), a "复制 Markdown" button with a menu (copy, or open the
  Markdown in a new tab), a language picker (English marked as coming), a sidebar that hides, a
  light and dark theme shared with the promo page, a drawer on narrow screens, and `llms.txt` plus each page's Markdown for
  models. The build fails on a link to a missing page or a page not in the sidebar.
- `.github/workflows/pages.yml` builds the docs, and now also runs on pull requests that touch
  `site/` (build only, no deploy).
- Languages: `docs/<language>/`, the frame's words in `site/_docs/i18n.toml`, a menu of nine
  languages (English and Chinese published, the other seven marked as coming), a page a
  language lacks shown in English with a notice, and `docs/` opening the reader's language
  (the one picked before, the promo page's, then the browser's).
- 27 pages in English and Chinese, in eight groups: Get started; Use coscribe (conversations,
  approvals, plans, files and panels, the browser, models and effort); Workspaces; Office files
  (Word, Excel, PowerPoint, PDF, artifacts); Scheduled tasks and workflows; Customize
  (instructions, skills and plugins, connectors, design systems); Reference (every setting,
  commands and shortcuts); Help (privacy and safety, troubleshooting with `/doctor`). Each label
  and behaviour was read from the frontend or the server, not from memory. Every heading has the
  same id in both languages, so a link to a section works from either.
- The promo page links to the docs from its top bar and footer. Its Download button pointed at
  `releases/latest`, which skips pre-releases, and every release so far is one, so it led to a
  404; it now opens the `beta` release.

## Not verified
- The Pages deploy itself: it runs only from `main`. The build was run here and the pages were
  looked at in Chromium on Linux, light, dark and at phone width.

## Follow-ups
- Spanish, Japanese, Portuguese (Brazil), Russian, French, Korean and German.
- The promo page's Settings mock still shows the old categories (Tools, Environment), and newer
  features are not on it.
- A Help entry in the app that opens the docs, and "Learn more" links next to settings.
