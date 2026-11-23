# The user docs

The pages at `<site>/docs/`: how to use coscribe, for the people who use it, not for the people
who build it. One Markdown file per page in `content/`, in the order `nav.toml` gives;
`build.py` adds the frame (sidebar, breadcrumbs, "本页内容", search) and writes `site/docs/`,
which is not committed. The Pages workflow builds it on every pull request that touches `site/`
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
- Name the UI exactly as it reads in the app, in bold (**Settings › Providers**), and say in
  Chinese what it does: the app's UI is English, the readers mostly read Chinese.
- Link another page by its file, relative to this one (`../get-started/providers.md#anchor`), so
  the link works on GitHub too. A `## Heading {#id}` sets an anchor by hand.
- Callouts: a quote starting with `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]` or `[!WARNING]`.
- Pictures go in `content/images/` and are linked relative to the page.
- Say only what the app does now; check it in the code or the running app, not in a log.
