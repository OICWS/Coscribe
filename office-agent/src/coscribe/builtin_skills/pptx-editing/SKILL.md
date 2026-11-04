---
name: PPTX Editing
description: Which tool changes what in an existing .pptx beyond one slide's text -- slides (delete, copy, reorder), shapes and SmartArt, diagrams built shape by shape, formulas, pictures, icons, tables, hyperlinks and theme colors -- and the mistakes to avoid with each. Load before any of those edits.
---
These edits work on any .pptx: one the user brought or one you built. Read the slide first
(`read_pptx`, `list_pptx_shapes`) and change only what was asked; everything else in the file stays
as it was.

## Slides: delete, copy, reorder

To change an existing .pptx's slide structure rather than one slide's content -- remove a slide,
copy one, or reorder them -- use delete_pptx_slide(path, slide), duplicate_pptx_slide(path, slide,
insert_at) (copies every shape/image on the source slide; defaults to inserting right after it;
speaker notes are not carried over to the copy), and reorder_pptx_slide(path, slide, new_position)
(1-based).

## Shapes: move, resize, recolor, delete; SmartArt

To move, resize, rotate, or recolor one existing shape on an existing .pptx (a real uploaded
template, or a deck you already generated) without rebuilding the slide, call list_pptx_shapes(path,
slide) first -- it lists every shape's index, type, position/size, rotation, a text preview, and
fill color -- then edit_pptx_shape(path, slide, shape_index, left_in, top_in, width_in, height_in,
rotation, fill_color) with only the properties you're changing -- add fill_color_2 (and optionally
gradient_angle) for a two-stop linear gradient fill instead of solid, or text_color to recolor every
run of text already in the shape (a title/body placeholder is a shape like any other here -- this is
the tool for "make this title a different color", not edit_pptx_theme_colors, see below). Never
guess shape_index without calling list_pptx_shapes first on a slide you haven't already inspected.
To remove a shape entirely (any type -- a plain shape, a picture, a table, or real SmartArt), call
delete_pptx_shape(path, slide, shape_index) with that same shape_index; this can't be undone.
list_pptx_shapes also flags real SmartArt (is_smartart: true) and lists each of its nodes' own text
(smartart_text). Neither this tool nor python-pptx can generate a *new* SmartArt diagram or change
its layout (the layout algorithm lives in PowerPoint itself, not the file format) -- if the user
wants a new diagram or a different layout, delete_pptx_shape it and rebuild the same idea using this
file's other shape/icon/table tools (e.g. write_pptx's own icon-list layout for a simple step/point
list). But changing an *existing* SmartArt node's own text in place is possible: call
read_pptx_xml(path, slide, shape_index) first (its `part="auto"` default reaches the real linked
data part SmartArt's text actually lives in, not the shape's own inline XML) to see the real <dgm:t>
structure, then edit_pptx_xml with an xpath that matches exactly the one text element to change --
don't reach for delete-and-rebuild just to fix a typo or reword one node.

## Diagrams built shape by shape

To build a specific diagram (a process flow of arrows and boxes, a decision tree, a comparison of
callouts) shape by shape at exact positions -- something write_pptx's own icon-list/stat-callout
layouts don't cover, since those position their own shapes automatically -- call
list_pptx_shape_types() for the available preset names (arrows, flowchart nodes, callouts, basic
shapes), then add_pptx_shape(path, slide, shape_type, left_in, top_in, width_in, height_in, text,
fill_color, line_color) once per shape. It returns the new shape's own shape_index, so a follow-up
edit_pptx_shape/add_pptx_hyperlink call can target it directly without a separate list_pptx_shapes
round-trip. **A plain geometric arrow/box/flowchart-node request -- "add an arrow", "add a green
box" -- means add_pptx_shape, never add_pptx_icon below, even though a same-ish-sounding icon (e.g.
a "trending-up" pictogram) might exist:** add_pptx_icon inserts a *raster picture*, which has no
`fill`/`fill_color_2`/`line_color` to set afterward and can only be recolored as one flat tint
(recolor_pptx_icon) -- reaching for it on a "shape" request is what silently makes a later "give it
a gradient" follow-up impossible to fulfill. Reserve add_pptx_icon (below) for when the user
actually wants a recognizable pictogram (a gear, a lightbulb, a checkmark glyph), not a generic
geometric shape that happens to share a name with one.

## Formulas

For actual mathematical notation -- a fraction, a square root, a summation, a matrix, a
subscript/superscript -- call add_pptx_formula(path, slide, latex, left_in, top_in, width_in,
height_in, display) instead of typing an approximation with Unicode characters (√, ², etc.) via
edit_pptx_text: it produces a real, natively-editable PowerPoint equation object (the same thing
PowerPoint's own Insert > Equation creates), not a plain text run that only looks right in one font.
`latex` is the documented Microsoft 365 LaTeX input PowerPoint's own equation editor accepts (e.g.
"\frac{-b \pm \sqrt{b^2-4ac}}{2a}"); `display=True` (default) for a centered standalone equation,
`display=False` for a smaller inline-sized one. Unsupported/malformed LaTeX raises a clear error
rather than silently guessing -- if that happens, simplify the formula or fall back to a plain-text
approximation and say so, don't retry the same LaTeX repeatedly.

## Pictures: replace and crop

To swap out an existing picture (a photo, an icon) for a different one on an existing .pptx without
touching its position, size, or crop, find its shape_index via list_pptx_shapes (is_picture: true)
then call replace_pptx_image(path, slide, shape_index, image_path). To crop an existing picture
(change which part of the image shows through its own on-slide box, without moving or resizing that
box) instead, call crop_pptx_image(path, slide, shape_index, crop_left, crop_right, crop_top,
crop_bottom) -- each a 0.0-1.0 fraction of the image's own width/height to trim from that edge, all
four given together each call.

## Icons

To add a real icon (not write_pptx's own icon-list glyph-in-a-circle) to a slide -- either one
you're editing or one you're building -- call list_pptx_icons() to see the available names, then
add_pptx_icon(path, slide, icon_name, left_in, top_in, size_in, color) to insert it as a square
picture at that position/size/color. To change an already- placed icon's color without moving or
resizing it, find its shape_index via list_pptx_shapes (is_picture: true) then call
recolor_pptx_icon(path, slide, shape_index, color) -- this recolors from the icon's own current
transparency, so it only makes sense on an icon/logo-style picture with real transparent background,
not a photo.

## Tables

To fix or update one value in an existing table (on a real uploaded template or a deck you already
generated) without rebuilding the whole slide, use list_pptx_shapes to find the table's shape_index
and table_dimensions, then edit_pptx_table_cell(path, slide, shape_index, row, col, text) with
0-based row/col to replace that one cell's text -- every other cell is untouched.
merge_pptx_table_cells(path, slide, shape_index, start_row, start_col, end_row, end_col) merges a
rectangular range into one cell (e.g. a spanning header) -- the merged cell keeps every merged-away
cell's text, appended as extra paragraphs, so clear a cell first with edit_pptx_table_cell if you
don't want its old text carried into the merge.

## Hyperlinks

To make a shape or a specific piece of text clickable, call add_pptx_hyperlink(path, slide,
shape_index, url, text). Find shape_index via list_pptx_shapes first (it also reports each shape's
current hyperlink, if any). Omit text to make the whole shape (an image, an icon, a whole textbox)
clickable; pass text to link just one run inside a text frame -- it must match that run's text
exactly (one whole word or phrase with its own formatting, not a substring you pick out of a longer
run). url must be an external http(s)/mailto/ftp address -- linking to another slide in the same
deck isn't supported.

## Theme colors

To see or change an existing .pptx's real master theme colors -- the same 12 colors
(dk1/lt1/dk2/lt2/accent1-6/hlink/folHlink) PowerPoint's own Design tab "Customize Colors" dialog
edits -- call read_pptx_theme_colors(path) first, then edit_pptx_theme_colors(path, colors) with
comma-separated slot=hexcolor pairs, e.g. "accent1=0F6B5C,accent2=C2410C". This changes every
placeholder/shape across the whole deck that references a theme color, so confirm with the user
which slot they actually mean (a slot name doesn't self-evidently map to "the color in the title"
without reading it first) before editing -- this is the most far-reaching single edit in this tool
file. **Set the user's expectations honestly before calling it, not after: this tool does NOT
recolor plain title/body text** -- that text is drawn from dk1 (or an explicit literal color), not
accent1-6, on both Coscribe's own generated decks (icon-list circles, stat-callout cards, and scrims
use hardcoded colors too, not theme references) and most real uploaded/downloaded templates. Calling
edit_pptx_theme_colors and then telling the user their titles are now a new color is a real mistake
to avoid -- verify with read_pptx_theme_colors or list_pptx_shapes if genuinely unsure, don't assume
accent1 governs text just because it sounds like it should. If the user's actual goal is "make this
text a different color", that is edit_pptx_shape's own text_color parameter (above), not this tool
-- and if that still doesn't land as expected, say so plainly rather than reaching for
run_node_script/ run_python_script to hand-roll a fix; guessing at python-pptx's fill/color API from
memory is exactly how a real mistake compounds into several.
