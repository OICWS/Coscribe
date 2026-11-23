"""Builds the user documentation in site/docs/ from the Markdown in site/_docs/content/.

The pages are plain Markdown so that a session changing a feature can change its page in the
same pull request, and so the app's own model can read them; this script only adds the frame.

    python site/_docs/build.py            # writes site/docs/
    python site/_docs/build.py --check    # builds into a temporary folder; fails on a broken link

Each language is a folder: content/en/ is the reference, and every page must exist there.
A published language that lacks a page shows the English one with a notice.

Needs markdown-it-py (pinned in .github/workflows/pages.yml).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import tomllib
from markdown_it import MarkdownIt

HERE = Path(__file__).resolve().parent
CONTENT = HERE / "content"
SITE = HERE.parent
REPO_BLOB = "https://github.com/OICWS/coscribe/blob/main/site/_docs/content/"
REFERENCE = "en"

# Drawn for these docs, in the spirit of the GitHub alert icons: info, bulb, flag, triangle.
_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>'
)
CALLOUT_ICONS = {
    "note": _ICON.format(
        '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.6v.1"/>'
    ),
    "tip": _ICON.format(
        '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.2 1 2V16h5.2v-.2'
        'c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z"/>'
    ),
    "important": _ICON.format(
        '<path d="M4 4.5h16v11H9.5L5 19.5v-4H4z"/><path d="M12 7.5v4M12 13.6v.1"/>'
    ),
    "warning": _ICON.format(
        '<path d="M12 3.5 21.5 20h-19z"/><path d="M12 10v4.5M12 16.9v.1"/>'
    ),
}
CHECK = (
    '<svg class="check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>'
)


# Only the face a language needs: each CJK family is several hundred kilobytes of subsets.
CJK_FONTS = {
    "zh": "&family=Noto+Sans+SC:wght@400;500;600;700",
    "ja": "&family=Noto+Sans+JP:wght@400;500;600;700",
    "ko": "&family=Noto+Sans+KR:wght@400;500;600;700",
}


@dataclass
class Page:
    lang: str
    slug: str  # "get-started/install", or "" for the docs home
    title: str
    description: str
    source: Path
    fallback: bool = False  # shown from English because this language lacks it
    group: str = ""
    body: str = ""
    body_md: str = ""
    toc: list[tuple[int, str, str]] = field(default_factory=list)
    text: str = ""


class BuildError(Exception):
    pass


def front_matter(raw: str, path: Path) -> tuple[dict[str, str], str]:
    # Only "key: value" lines: a YAML parser would be one more dependency for two fields.
    if not raw.startswith("---\n"):
        raise BuildError(f"{rel(path)}: starts without a --- front matter block")
    end = raw.index("\n---\n", 4)
    meta = {}
    for line in raw[4:end].splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    if not meta.get("title"):
        raise BuildError(f"{rel(path)}: has no title")
    return meta, raw[end + 5 :]


def rel(path: Path) -> str:
    return path.relative_to(SITE).as_posix()


def slugify(text: str) -> str:
    # Headings in Chinese, Japanese or Korean keep their characters, so an anchor still says
    # what it points to.
    text = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"[\s_]+", "-", text).strip("-") or "section"


def page_path(lang: str, slug: str) -> Path:
    return CONTENT / lang / (f"{slug}.md" if slug else "index.md")


def load(groups: list[dict], lang: str) -> dict[str, Page]:
    slugs = ["", *(f"{g['id']}/{n}" for g in groups for n in g["pages"])]
    if len(set(slugs)) != len(slugs):
        raise BuildError("nav.toml lists a page twice")
    pages: dict[str, Page] = {}
    for slug in slugs:
        path = page_path(lang, slug)
        fallback = not path.exists()
        if fallback:
            if lang == REFERENCE:
                raise BuildError(
                    f"nav.toml names {slug or 'index'!r}, but {rel(path)} does not exist"
                )
            path = page_path(REFERENCE, slug)
        meta, body = front_matter(path.read_text(encoding="utf-8"), path)
        page = Page(
            lang, slug, meta["title"], meta.get("description", ""), path, fallback
        )
        page.body = page.body_md = body
        page.group = slug.partition("/")[0]
        pages[slug] = page
    listed = {page_path(lang, s) for s in slugs}
    for path in (CONTENT / lang).rglob("*.md"):
        if path not in listed:
            raise BuildError(f"{rel(path)} is not listed in nav.toml")
    return pages


def render(page: Page, pages: dict[str, Page], md: MarkdownIt, words: dict) -> None:
    tokens = md.parse(page.body)
    used: set[str] = set()
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open" and tok.tag in ("h2", "h3"):
            inline = tokens[i + 1]
            explicit = re.search(r"\s*\{#([\w-]+)\}$", inline.content)
            if explicit:
                anchor = explicit.group(1)
                inline.content = inline.content[: explicit.start()]
                inline.children[-1].content = re.sub(
                    r"\s*\{#[\w-]+\}$", "", inline.children[-1].content
                )
            else:
                anchor = slugify(inline.content)
            base, n = anchor, 2
            while anchor in used:
                anchor, n = f"{base}-{n}", n + 1
            used.add(anchor)
            tok.attrSet("id", anchor)
            page.toc.append((int(tok.tag[1]), inline.content, anchor))
        if tok.type == "blockquote_open":
            inline = next((t for t in tokens[i + 1 :] if t.type == "inline"), None)
            m = inline and re.match(r"\[!(\w+)\]\s*", inline.content)
            if m and m.group(1).lower() in CALLOUT_ICONS:
                kind = m.group(1).lower()
                tok.attrSet("class", f"callout callout-{kind}")
                inline.content = inline.content[m.end() :]
                first = inline.children[0]
                first.content = re.sub(r"^\[!\w+\]\s*", "", first.content)
                if (
                    not first.content
                    and len(inline.children) > 1
                    and inline.children[1].type == "softbreak"
                ):
                    del inline.children[:2]
        for t in [tok, *(tok.children or [])]:
            for attr in ("href", "src"):
                value = t.attrGet(attr)
                if value:
                    t.attrSet(attr, link_target(value, page, pages))
    body = md.renderer.render(tokens, md.options, {})
    body = re.sub(
        r'<blockquote class="callout callout-(\w+)">\n?',
        lambda m: (
            f'<blockquote class="callout callout-{m.group(1)}">'
            f'<p class="callout-title">{CALLOUT_ICONS[m.group(1)]}{esc(words[m.group(1)])}</p>'
        ),
        body,
    )
    # A wide table scrolls inside its own box instead of the page.
    page.body = body.replace("<table>", '<div class="table-wrap"><table>').replace(
        "</table>", "</table></div>"
    )
    page.text = re.sub(
        r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page.body))
    ).strip()


def link_target(value: str, page: Page, pages: dict[str, Page]) -> str:
    """Rewrites a link to another page's source ("../models/providers.md#keys", relative to
    this file) to the built page's URL.

    Authors link by source file so a link works the same on GitHub and on the site, and the
    build fails on one that points nowhere.
    """
    if re.match(r"^[a-z]+:|^#|^//", value):
        return value
    path, _, anchor = value.partition("#")
    target = (page.source.parent / path).resolve()
    if target.is_relative_to(CONTENT / "images"):
        if not target.exists():
            raise BuildError(
                f"{rel(page.source)}: shows {path!r}, which does not exist"
            )
        return assets(page.slug) + target.relative_to(CONTENT).as_posix()
    lang_dir = CONTENT / page.source.relative_to(CONTENT).parts[0]
    if not path.endswith(".md") or not target.is_relative_to(lang_dir):
        raise BuildError(
            f"{rel(page.source)}: link {value!r} is neither a page of its language nor a picture"
        )
    slug = target.relative_to(lang_dir).as_posix()[:-3]
    slug = "" if slug == "index" else slug
    if slug not in pages:
        raise BuildError(f"{rel(page.source)}: links to {value!r}, which is no page")
    return url(page.slug, slug) + (f"#{anchor}" if anchor else "")


def root(slug: str) -> str:
    """The relative path from a page to its language's folder, docs/<lang>/."""
    return "../" * (slug.count("/") + 1) if slug else ""


def assets(slug: str) -> str:
    """The relative path from a page to docs/, where the shared CSS, script and pictures are."""
    return root(slug) + "../"


def url(from_slug: str, to_slug: str) -> str:
    return root(from_slug) + (f"{to_slug}/" if to_slug else "./")


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def sidebar(
    groups: list[dict], pages: dict[str, Page], current: Page, words: dict
) -> str:
    out = []
    for group in groups:
        items = []
        for name in group["pages"]:
            p = pages[f"{group['id']}/{name}"]
            active = ' aria-current="page"' if p is current else ""
            items.append(
                f'<li><a href="{url(current.slug, p.slug)}"{active}>{esc(p.title)}</a></li>'
            )
        is_open = " open" if group["id"] == current.group else ""
        title = esc(words["groups"][group["id"]]["title"])
        out.append(
            f'<details class="nav-group"{is_open}><summary>{title}'
            f'<i class="tri" aria-hidden="true"></i></summary><ul>{"".join(items)}</ul></details>'
        )
    return "".join(out)


def toc(page: Page, words: dict) -> str:
    if len(page.toc) < 2:
        return ""
    items = "".join(
        f'<li class="toc-h{level}"><a href="#{anchor}">{esc(title)}</a></li>'
        for level, title, anchor in page.toc
    )
    label = esc(words["toc"])
    return (
        f'<nav class="toc" aria-label="{label}"><h2>{label}</h2><ul>{items}</ul></nav>'
    )


def pager(order: list[Page], page: Page, words: dict) -> str:
    i = order.index(page)
    parts = []
    if i > 1:  # the docs home is not a step back from the first page
        p = order[i - 1]
        parts.append(
            f'<a class="pn prev" href="{url(page.slug, p.slug)}"><span>{esc(words["prev"])}</span>{esc(p.title)}</a>'
        )
    if 0 < i < len(order) - 1:
        p = order[i + 1]
        parts.append(
            f'<a class="pn next" href="{url(page.slug, p.slug)}"><span>{esc(words["next"])}</span>{esc(p.title)}</a>'
        )
    if not parts:
        return ""
    return (
        f'<nav class="pager" aria-label="{esc(words["pager"])}">{"".join(parts)}</nav>'
    )


def home_cards(groups: list[dict], pages: dict[str, Page], words: dict) -> str:
    cards = []
    for group in groups:
        links = "".join(
            f'<li><a href="{url("", p.slug)}">{esc(p.title)}</a></li>'
            for p in (pages[f"{group['id']}/{n}"] for n in group["pages"])
        )
        g = words["groups"][group["id"]]
        cards.append(
            f'<section class="card"><h2>{esc(g["title"])}</h2>'
            f"<p>{esc(g.get('description', ''))}</p><ul>{links}</ul></section>"
        )
    return f'<div class="cards">{"".join(cards)}</div>'


def language_menu(langs: dict, current: str, slug: str) -> str:
    items = []
    for code, w in langs.items():
        name = esc(w["name"])
        if not w.get("published"):
            soon = esc(langs[current]["coming_soon"])
            items.append(
                f'<span class="menu-item" role="menuitem" aria-disabled="true" lang="{w["html_lang"]}">'
                f"<span></span><span><b>{name}</b><small>{soon}</small></span><span></span></span>"
            )
            continue
        here = code == current
        href = assets(slug) + code + "/" + (f"{slug}/" if slug else "")
        items.append(
            f'<a class="menu-item" role="menuitemradio" aria-checked="{str(here).lower()}" '
            f'href="{href}" hreflang="{w["html_lang"]}" lang="{w["html_lang"]}" data-lang="{code}">'
            f"{CHECK if here else '<span></span>'}<span><b>{name}</b></span><span></span></a>"
        )
    return "".join(items)


def build_language(
    out: Path, lang: str, langs: dict, groups: list[dict], md: MarkdownIt, template: str
) -> list[Page]:
    words = {**langs[REFERENCE], **langs[lang]}
    words["groups"] = {
        g["id"]: {
            **langs[REFERENCE]["groups"][g["id"]],
            **langs[lang].get("groups", {}).get(g["id"], {}),
        }
        for g in groups
    }
    pages = load(groups, lang)
    for page in pages.values():
        render(page, pages, md, words)
    order = list(pages.values())

    for page in order:
        is_home = not page.slug
        crumbs = [f'<a href="{url(page.slug, "")}">{esc(words["docs"])}</a>']
        if not is_home:
            first = next(n for g in groups if g["id"] == page.group for n in g["pages"])
            title = esc(words["groups"][page.group]["title"])
            crumbs.append(
                f'<a href="{url(page.slug, page.group + "/" + first)}">{title}</a>'
            )
            crumbs.append(f'<span aria-current="page">{esc(page.title)}</span>')
        source = page.source.relative_to(CONTENT).as_posix()
        md_name = f"{page.slug}.md" if page.slug else "index.md"
        notice = ""
        if page.fallback:
            notice = f'<p class="untranslated">{esc(words["untranslated"].format(lang=words["name"]))}</p>'
        values = {
            "lang": langs[lang]["html_lang"],
            "fonts": CJK_FONTS.get(lang, ""),
            "lang_code": lang,
            "title": esc(
                page.title if is_home else f"{page.title} · {words['docs_title']}"
            ),
            "description": esc(page.description),
            "root": root(page.slug),
            "assets": assets(page.slug),
            "site": assets(page.slug) + "../",
            "sidebar": sidebar(groups, pages, page, words),
            "crumbs": '<span class="sep">/</span>'.join(crumbs),
            "h1": esc(page.title),
            "lead": f'<p class="lead">{esc(page.description)}</p>'
            if page.description
            else "",
            "notice": notice,
            "markdown_url": root(page.slug) + md_name,
            "edit_url": REPO_BLOB + source,
            "body": page.body + (home_cards(groups, pages, words) if is_home else ""),
            "toc": toc(page, words),
            "pager": pager(order, page, words),
            "page_class": "home" if is_home else "article",
            "language_name": esc(words["name"]),
            "language_menu": language_menu(langs, lang, page.slug),
            # Inside <script> nothing is entity-decoded, so the JSON is only kept from closing it.
            "strings": json.dumps(
                {k: words[k] for k in ("search_empty", "copy_failed", "anchor")},
                ensure_ascii=False,
            ).replace("</", "<\\/"),
        }
        values.update(
            {f"t_{k}": esc(v) for k, v in words.items() if isinstance(v, str)}
        )
        rendered = re.sub(r"\{\{(\w+)\}\}", lambda m, v=values: v[m.group(1)], template)
        target = (
            out / lang / page.slug / "index.html"
            if page.slug
            else out / lang / "index.html"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        # The published Markdown carries its title, so a copy pasted into a chat stands alone.
        md_copy = out / lang / md_name
        md_copy.parent.mkdir(parents=True, exist_ok=True)
        md_copy.write_text(
            f"# {page.title}\n\n{page.description}\n\n{page.body_md.lstrip()}",
            encoding="utf-8",
        )

    index = [
        {
            "t": p.title,
            "g": words["groups"][p.group]["title"] if p.slug else "",
            "u": f"{lang}/{p.slug}/" if p.slug else f"{lang}/",
            "h": [t for _, t, _ in p.toc],
            "x": p.text[:4000],
        }
        for p in order
    ]
    (out / lang / "search.json").write_text(
        json.dumps(index, ensure_ascii=False), encoding="utf-8"
    )
    llms = [f"# {words['docs_title']}", "", f"> {words['llms_summary']}", ""]
    for group in groups:
        llms.append(f"## {words['groups'][group['id']]['title']}")
        for name in group["pages"]:
            p = pages[f"{group['id']}/{name}"]
            llms.append(f"- [{p.title}]({p.slug}.md): {p.description}")
        llms.append("")
    (out / lang / "llms.txt").write_text("\n".join(llms), encoding="utf-8")
    return order


def build(out: Path) -> int:
    langs = tomllib.loads((HERE / "i18n.toml").read_text(encoding="utf-8"))
    groups = tomllib.loads((HERE / "nav.toml").read_text(encoding="utf-8"))["group"]
    for code in CONTENT.iterdir():
        if (
            code.is_dir()
            and code.name != "images"
            and not langs.get(code.name, {}).get("published")
        ):
            raise BuildError(
                f"content/{code.name}/ is not a published language in i18n.toml"
            )
    missing = [k for k in langs[REFERENCE] if isinstance(langs[REFERENCE][k], str)]
    for code, w in langs.items():
        if w.get("published"):
            gaps = [k for k in missing if k not in w]
            if gaps:
                raise BuildError(
                    f"i18n.toml: {code} is published but lacks {', '.join(gaps)}"
                )
    md = MarkdownIt(
        "commonmark", {"html": True, "linkify": False, "typographer": False}
    )
    md.enable(["table", "strikethrough"])
    template = (HERE / "template.html").read_text(encoding="utf-8")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for asset in ("docs.css", "docs.js"):
        shutil.copy(HERE / asset, out / asset)
    if (CONTENT / "images").exists():
        shutil.copytree(CONTENT / "images", out / "images")
    count = 0
    published = [code for code, w in langs.items() if w.get("published")]
    for code in published:
        count += len(build_language(out, code, langs, groups, md, template))
    redirect = (HERE / "redirect.html").read_text(encoding="utf-8")
    choices = {code: langs[code]["html_lang"] for code in published}
    (out / "index.html").write_text(
        redirect.replace("{{choices}}", json.dumps(choices)).replace(
            "{{links}}",
            "".join(
                f'<li><a href="{c}/" hreflang="{h}">{esc(langs[c]["name"])}</a></li>'
                for c, h in choices.items()
            ),
        ),
        encoding="utf-8",
    )
    shutil.copy(out / REFERENCE / "llms.txt", out / "llms.txt")
    (out / "llms.txt").write_text(
        (out / "llms.txt").read_text(encoding="utf-8").replace("](", f"]({REFERENCE}/"),
        encoding="utf-8",
    )
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="build into a temporary folder"
    )
    args = parser.parse_args()
    try:
        if args.check:
            with tempfile.TemporaryDirectory() as tmp:
                count = build(Path(tmp) / "docs")
        else:
            count = build(SITE / "docs")
    except BuildError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    print(f"built {count} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
