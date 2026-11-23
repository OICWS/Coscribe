# User docs on the website: the frame and the Get started pages (partly shipped)

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
- Four pages in Chinese under 入门: what coscribe is, download and first start, providers, the
  first conversation (including the four permission modes).
- The promo page links to the docs from its top bar and footer. Its Download button pointed at
  `releases/latest`, which skips pre-releases, and every release so far is one, so it led to a
  404; it now opens the `beta` release.

## Not verified
- The Pages deploy itself: it runs only from `main`. The build was run here and the pages were
  looked at in Chromium on Linux, light, dark and at phone width.

## Follow-ups
- The rest of the outline: daily use, Office files, workflows, workspaces, models, customizing,
  the settings reference, privacy, troubleshooting.
- English pages, once the Chinese ones settle.
- The promo page's Settings mock still shows the old categories (Tools, Environment), and newer
  features are not on it.
- A Help entry in the app that opens the docs, and "Learn more" links next to settings.
