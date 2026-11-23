"""Builds the user documentation in site/docs/ from the Markdown in site/_docs/content/.

The pages are plain Markdown so that a session changing a feature can change its page in the
same pull request, and so the app's own model can read them; this script only adds the frame.

    python site/_docs/build.py            # writes site/docs/
    python site/_docs/build.py --check    # builds into a temporary folder; fails on a broken link

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

CALLOUTS = {
    "NOTE": "说明",
    "TIP": "提示",
    "IMPORTANT": "重要",
    "WARNING": "注意",
}


@dataclass
class Page:
    slug: str  # "get-started/install", or "" for the docs home
    title: str
    description: str
    source: Path
    group: str = ""
    group_title: str = ""
    body: str = ""
    toc: list[tuple[int, str, str]] = field(default_factory=list)
    text: str = ""


class BuildError(Exception):
    pass


def front_matter(raw: str, path: Path) -> tuple[dict[str, str], str]:
    # Only "key: value" lines: a YAML parser would be one more dependency for two fields.
    if not raw.startswith("---\n"):
        raise BuildError(f"{path}: starts without a --- front matter block")
    end = raw.index("\n---\n", 4)
    meta = {}
    for line in raw[4:end].splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    if not meta.get("title"):
        raise BuildError(f"{path}: has no title")
    return meta, raw[end + 5 :]


def slugify(text: str) -> str:
    # Chinese headings keep their characters, so an anchor still says what it points to.
    text = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"[\s_]+", "-", text).strip("-") or "section"


def load_pages() -> tuple[list[dict], dict[str, Page]]:
    nav = tomllib.loads((HERE / "nav.toml").read_text(encoding="utf-8"))
    pages: dict[str, Page] = {}

    def read(slug: str) -> Page:
        path = CONTENT / (slug or "index")
        path = path.with_suffix(".md") if slug else CONTENT / "index.md"
        if not path.exists():
            raise BuildError(
                f"nav.toml names {slug!r}, but {path.relative_to(SITE)} does not exist"
            )
        meta, body = front_matter(path.read_text(encoding="utf-8"), path)
        return Page(slug, meta["title"], meta.get("description", ""), path, body=body)

    pages[""] = read("")
    for group in nav["group"]:
        for name in group["pages"]:
            slug = f"{group['id']}/{name}"
            if slug in pages:
                raise BuildError(f"nav.toml lists {slug!r} twice")
            page = read(slug)
            page.group, page.group_title = group["id"], group["title"]
            pages[slug] = page
    listed = {p.source for p in pages.values()}
    for path in CONTENT.rglob("*.md"):
        if path not in listed:
            raise BuildError(f"{path.relative_to(SITE)} is not listed in nav.toml")
    return nav["group"], pages


def render(page: Page, pages: dict[str, Page], md: MarkdownIt) -> None:
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
            if m and m.group(1) in CALLOUTS:
                kind = m.group(1)
                tok.attrSet("class", f"callout callout-{kind.lower()}")
                tok.attrSet("data-label", CALLOUTS[kind])
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
    page.body = md.renderer.render(tokens, md.options, {})
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
    try:
        rel = target.relative_to(CONTENT).as_posix()
    except ValueError:
        raise BuildError(
            f"{page.source.relative_to(SITE)}: link {value!r} leaves the docs"
        ) from None
    if path.endswith(".md"):
        slug = rel[:-3]
        slug = "" if slug == "index" else slug
        if slug not in pages:
            raise BuildError(
                f"{page.source.relative_to(SITE)}: links to {value!r}, which is no page"
            )
        return url(page.slug, slug) + (f"#{anchor}" if anchor else "")
    if rel.startswith("images/"):
        if not target.exists():
            raise BuildError(
                f"{page.source.relative_to(SITE)}: shows {path!r}, which does not exist"
            )
        return root(page.slug) + rel
    raise BuildError(
        f"{page.source.relative_to(SITE)}: link {value!r} is neither a page nor an image"
    )


def root(slug: str) -> str:
    """The relative path from a page back to docs/, so the site works under any base path."""
    return "../" * (slug.count("/") + 1) if slug else ""


def url(from_slug: str, to_slug: str) -> str:
    return root(from_slug) + (f"{to_slug}/" if to_slug else "./")


def sidebar(groups: list[dict], pages: dict[str, Page], current: Page) -> str:
    out = []
    for group in groups:
        is_open = group["id"] == current.group
        items = []
        for name in group["pages"]:
            p = pages[f"{group['id']}/{name}"]
            active = ' aria-current="page"' if p is current else ""
            items.append(
                f'<li><a href="{url(current.slug, p.slug)}"{active}>{esc(p.title)}</a></li>'
            )
        out.append(
            f'<details class="nav-group"{" open" if is_open else ""}>'
            f"<summary>{esc(group['title'])}</summary><ul>{''.join(items)}</ul></details>"
        )
    return "".join(out)


def toc(page: Page) -> str:
    if len(page.toc) < 2:
        return ""
    items = "".join(
        f'<li class="toc-h{level}"><a href="#{anchor}">{esc(title)}</a></li>'
        for level, title, anchor in page.toc
    )
    return f'<nav class="toc" aria-label="本页内容"><h2>本页内容</h2><ul>{items}</ul></nav>'


def neighbours(order: list[Page], page: Page) -> str:
    i = order.index(page)
    parts = []
    if i > 0:
        p = order[i - 1]
        parts.append(
            f'<a class="pn prev" href="{url(page.slug, p.slug)}"><span>上一页</span>{esc(p.title)}</a>'
        )
    if i < len(order) - 1:
        p = order[i + 1]
        parts.append(
            f'<a class="pn next" href="{url(page.slug, p.slug)}"><span>下一页</span>{esc(p.title)}</a>'
        )
    return (
        f'<nav class="pager" aria-label="翻页">{"".join(parts)}</nav>' if parts else ""
    )


def home_cards(groups: list[dict], pages: dict[str, Page]) -> str:
    cards = []
    for group in groups:
        links = "".join(
            f'<li><a href="{url("", p.slug)}">{esc(p.title)}</a></li>'
            for p in (pages[f"{group['id']}/{n}"] for n in group["pages"])
        )
        cards.append(
            f'<section class="card"><h2>{esc(group["title"])}</h2>'
            f"<p>{esc(group.get('description', ''))}</p><ul>{links}</ul></section>"
        )
    return f'<div class="cards">{"".join(cards)}</div>'


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def build(out: Path) -> int:
    groups, pages = load_pages()
    md = MarkdownIt(
        "commonmark", {"html": True, "linkify": False, "typographer": False}
    )
    md.enable(["table", "strikethrough"])
    for page in pages.values():
        render(page, pages, md)

    order = [pages[""], *(p for p in pages.values() if p.slug)]
    template = (HERE / "template.html").read_text(encoding="utf-8")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for asset in ("docs.css", "docs.js"):
        shutil.copy(HERE / asset, out / asset)
    if (CONTENT / "images").exists():
        shutil.copytree(CONTENT / "images", out / "images")

    for page in order:
        is_home = not page.slug
        crumbs = [f'<a href="{url(page.slug, "")}">文档</a>']
        if not is_home:
            first = next(n for g in groups if g["id"] == page.group for n in g["pages"])
            crumbs.append(
                f'<a href="{url(page.slug, page.group + "/" + first)}">{esc(page.group_title)}</a>'
            )
            crumbs.append(f'<span aria-current="page">{esc(page.title)}</span>')
        source = page.source.relative_to(CONTENT).as_posix()
        values = {
            "title": esc(page.title if is_home else f"{page.title} · coscribe 文档"),
            "description": esc(page.description),
            "root": root(page.slug),
            "site": root(page.slug) + "../",
            "sidebar": sidebar(groups, pages, page),
            "crumbs": '<span class="sep">/</span>'.join(crumbs),
            "h1": esc(page.title),
            "lead": f'<p class="lead">{esc(page.description)}</p>'
            if page.description
            else "",
            "markdown_url": f"{root(page.slug)}{source}",
            "edit_url": REPO_BLOB + source,
            "body": page.body + (home_cards(groups, pages) if is_home else ""),
            "toc": toc(page),
            "pager": "" if is_home else neighbours(order, page),
            "page_class": "home" if is_home else "article",
        }
        rendered = re.sub(r"\{\{(\w+)\}\}", lambda m, v=values: v[m.group(1)], template)
        target = out / page.slug / "index.html" if page.slug else out / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        md_copy = out / source
        md_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(page.source, md_copy)

    index = [
        {
            "t": p.title,
            "g": p.group_title,
            "u": f"{p.slug}/" if p.slug else "",
            "h": [t for _, t, _ in p.toc],
            "x": p.text[:4000],
        }
        for p in order
    ]
    (out / "search.json").write_text(
        json.dumps(index, ensure_ascii=False), encoding="utf-8"
    )
    llms = [
        "# coscribe 用户文档",
        "",
        "> coscribe 是运行在 Windows 电脑上的开源办公助理。",
        "",
    ]
    for group in groups:
        llms.append(f"## {group['title']}")
        for name in group["pages"]:
            p = pages[f"{group['id']}/{name}"]
            llms.append(f"- [{p.title}]({p.slug}.md): {p.description}")
        llms.append("")
    (out / "llms.txt").write_text("\n".join(llms), encoding="utf-8")
    return len(order)


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
