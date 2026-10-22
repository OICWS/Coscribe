---
name: SVG and HTML Design
description: How to design icons, logos, illustrations and option sheets as one self-contained .html or .svg file the app shows in its Design panel -- load before making one.
---
A design is a single file. The app shows it in a sandboxed frame with no network, so it
must stand on its own: no CDN, no web fonts, no remote images, no links to other files.
Write it with `write_file`; to change it, write the same path again and the same artifact
updates.

## Which file

Always one `.html` file; that is what the app shows as a Design. Put every drawing inline
as `<svg>` inside it, even a single icon, with a title, a light and a dark background and
a size ladder (below). A lone `.svg` file is only a picture file, like a .png: the app does
not treat it as a design. Also write each finished drawing as its own `.svg` beside the page,
so the user can use it elsewhere.

## Drawing in SVG

- Give the root `<svg>` a `viewBox`; draw icons on a 0 0 128 128 grid with a margin of about 8.
- Put gradients (`linearGradient`, `radialGradient`) and filters (`feDropShadow`) in `<defs>`
  and refer to them by id. Ids are shared by the whole HTML page: prefix them per drawing
  (`a-grad`, `b-grad`) so two drawings never clash.
- Prefer a few bold shapes with 2 to 4 colours over many fine lines. A soft drop shadow
  (`dy` about 6% of the height, low opacity) gives depth without an outline.
- Convert text to paths for a logo; a font on the user's machine is not guaranteed.

## Showing options in HTML

- Define each drawing once as a `<symbol id="...">` with a `viewBox` in a hidden
  `<svg width="0" height="0" style="position:absolute">`, then draw it at each size with
  `<svg width="48" height="48"><use href="#id"/></svg>`.
- Show every option at 16, 32, 48, 64 and 128 px, on a light and on a dark background:
  an icon that works large often fails at 16 px. At small sizes drop fine detail instead of
  shrinking it.
- Label each option with a number and a short name, so the user can answer "number 3".
- Style with CSS variables defined on `:root`; add a `@media (prefers-color-scheme: dark)`
  block that redefines them, plus a `:root[data-theme="dark"]` one, and give `body` an
  explicit background.
- Lay out with CSS grid and `repeat(auto-fit, minmax(min(100%, 320px), 1fr))`; keep the
  page usable at 360 px wide with no horizontal scroll.

## Before you say it is done

Check that every id you refer to exists, that nothing loads from the network, and that the
file opens as plain text without errors. Say the file name and what each option is in one
line each; do not describe the shapes.
