# The user docs

The pages at `<site>/docs/<language>/`: how to use coscribe, for the people who use it, not for
the people who build it. One Markdown file per page in `content/<language>/`, in the order
`nav.toml` gives; `build.py` adds the frame (sidebar, breadcrumbs, "In this article", search,
language menu) and writes `site/docs/`, which is not committed. `docs/` itself opens the reader's
language.

## Languages

`i18n.toml` holds the frame's words per language and which languages are published. English
(`content/en/`) is the reference: every page exists there first. A published language that lacks
a page shows the English page with a notice, so a translation can land page by page. A page
changed in English changes in every language that has it, in the same pull request. The Pages workflow builds it on every pull request that touches `site/`
and publishes it from `main`.

```bash
pip install "markdown-it-py==4.3.0"
python site/_docs/build.py          # then serve site/ (python -m http.server -d site)
python site/_docs/build.py --check  # what CI runs: fails on a broken link or an unlisted page
```

## When a change makes a page untrue

A change to something a person sees (a button, a setting, a mode, a command) changes its page in
the same pull request. Search `content/` for the label the UI shows.

## Writing a page

- Front matter: `title` and a one-line `description` (it is the lead under the title and the
  search snippet).
- Name the UI exactly as it reads in the app, in bold (**Settings › Providers**): the app's UI is
  English in every language, so a translation keeps the label in English and says what it does.
- Link another page by its file, relative to this one (`../get-started/providers.md#anchor`), so
  the link works on GitHub too. A `## Heading {#id}` sets an anchor by hand.
- Callouts: a quote starting with `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]` or `[!WARNING]`.
- Pictures go in `content/images/`, shared by every language, and are linked relative to the page.
- Anchors that other pages link to are set by hand in every language (`## 权限模式 {#permission-modes}`),
  so one link works in all of them.
- Say only what the app does now; check it in the code or the running app, not in a log.
