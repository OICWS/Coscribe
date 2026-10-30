---
name: Design
description: Make a visual design the app opens on its Design canvas -- screens, a landing page, a poster, a social image, a logo or icon sheet, several options side by side -- as artboards on one canvas; load before making or changing one. A deck is Slides, a page of real data is a Dashboard, a document is a Doc.
---
A design is a canvas of artboards. The canvas is a small JSON file; each artboard is a page of
its own in the folder beside it, drawn at its real size in a sandboxed frame with no network: no
CDN, no web fonts, no remote images, no fetch. The person pans and zooms the canvas, moves the
artboards, leaves notes on it, and presses Play to use an artboard's page.

## The files

For a design named `launch`:

    launch.design.json           the canvas
    launch.design                a folder beside it, holding
      home.html                  one page per artboard
      home-phone.html

`launch.design.json`:

    {
      "boards": [
        {"id": "home", "title": "Home · desktop", "file": "home.html", "width": 1440, "height": 900},
        {"id": "home-phone", "title": "Home · phone", "file": "home-phone.html", "width": 390, "height": 844}
      ],
      "variables": [
        {"name": "--brand", "value": "#2557d6", "label": "Brand"},
        {"name": "--ink", "value": "#14161a", "label": "Text"},
        {"name": "--font", "value": "'Segoe UI', system-ui, sans-serif", "label": "Font"},
        {"name": "--radius", "value": "12px", "label": "Corner radius"}
      ]
    }

- Write the pages first, then the canvas, each with `write_file`.
- Leave out `x` and `y`: the app puts each board to the right of the one before it. Give them only
  to lay boards out in rows (the same `y` for a row, about 80 apart).
- Ids are letters, digits, `-` and `_`; a `file` is a plain `.html` name in the folder.

## Artboards

- Size each board for what it is: desktop 1440×900, laptop 1280×800, tablet 834×1194, phone
  390×844, A4 poster 794×1123, social square 1080×1080, story 1080×1920, link preview 1200×630.
  A long web page is 1440 wide and as tall as its content.
- Options are artboards: when the person wants to choose, make two to four, titled with a number
  and a short name (`1 · Calm`, `2 · Bold`), so they can answer "number 2". Make them really
  different (layout, type, colour), not one design in three colours.
- The same screen at several sizes is several artboards, one per size, side by side.
- The page fills its board exactly: `html, body { margin: 0; width: 100%; height: 100%; }` and a
  layout made for that width. No scroll bars unless the board is a long page.
- Write real content (the person's product, words and numbers where they gave them), not lorem
  ipsum. Where they gave none, write plausible text and say so.

## Variables: the design system

The canvas's `variables` are the design system every artboard shares: brand colours, the text
colour, the fonts, corner radius, a spacing unit. The app puts them into every page's `:root`
after the page's own styles, and the person can change them on the canvas, so:

- In the pages, use `var(--brand)` and the others for everything they cover; never write the same
  colour or font as a literal. A page may define them too in its own `:root` (so it reads well as
  a file), but the canvas's value wins.
- Name what a variable is for (`--brand`, `--surface`, `--ink`), give it a `label`, and keep the
  list short, about four to ten.
- A value is a colour (`#2557d6`), a length (`12px`), a font stack or a number; no `;`, `{`, `}`,
  `<` or `>`.
- When the conversation names a design system, its colours, fonts, sizes and radius become the
  variables.

## Inside a page

- Self-contained: styles in `<style>`, scripts inline. Fonts are local stacks (`'Segoe UI',
  system-ui, sans-serif`; `Georgia, serif`). Pictures are inline `<svg>` or `data:` URIs; draw
  illustrations, icons and charts as SVG.
- A script may make the page work when the person presses Play: tabs, a menu that opens, a form
  that checks its fields. It reaches nothing outside the page.
- Text a person might change is real text in the page, not drawn into an SVG.
- The canvas shows the artboards light or dark as the person switches. Give a page its dark look
  in `@media (prefers-color-scheme: dark)` or under `:root[data-theme="dark"]`, with the surface
  and text colours there; a design that is only light or only dark needs neither.

## Logos and icons

A logo or icon sheet is an artboard (about 1200 wide) with each option at 16, 32, 48, 64 and 128 px
on a light and a dark background: an icon that works large often fails at 16 px, so drop fine
detail at small sizes instead of shrinking it.

- Define each drawing once as a `<symbol id="...">` with a `viewBox` in a hidden
  `<svg width="0" height="0" style="position:absolute">`, then draw it at each size with
  `<svg width="48" height="48"><use href="#id"/></svg>`. Draw icons on a 0 0 128 128 grid with a
  margin of about 8.
- Ids are shared by the whole page: prefix them per drawing (`a-grad`, `b-grad`).
- Prefer a few bold shapes with 2 to 4 colours over many fine lines; a soft drop shadow
  (`feDropShadow`, `dy` about 6% of the height, low opacity) gives depth without an outline.
- Convert a logo's text to paths. Also write each finished drawing as its own `.svg` beside the
  canvas, so the person can use it elsewhere.

## Changing a design

- To change an artboard, write its page again: the canvas redraws it.
- The person moves boards and leaves notes, which the app saves into the canvas file. Read the
  file before you write it, and keep every board's `x`, `y`, `width` and `height`, the variables'
  values and the `notes` as they are, unless you are asked to change them. A note is the person's
  comment on the design: do what it asks, then leave it unless they say to remove it.
- To add an option, add a page and a board; to drop one, remove its board (and say so).

## Before you say it is done

Check that every board's `file` exists, that every `var(--...)` a page uses is a variable of the
canvas or defined in the page, that every SVG id you refer to exists, and that nothing loads from
the network. Say the canvas's file name and one line per artboard; do not describe the shapes.
