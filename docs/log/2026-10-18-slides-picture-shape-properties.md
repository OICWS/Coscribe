# Pictures and shapes have properties panels

Why: selecting a picture or a shape showed nothing in the properties panel (decision 0017's
follow-on: one panel per kind of object).

## Shipped
- Picture (`SlideObjectProperties.tsx`, `ImageProperties`): the file's name with Replace (a new
  picture is saved into the deck and takes the `src`), Fit (Cover, Contain, Stretch) and Alt text.
- Shape (`ShapeProperties`): background, opacity (number and slider), radius (a rounded
  rectangle), border (none, solid or dashed) with its width and colour. A line has no
  background and keeps a border, which is how it is drawn.
- `lib/slideShape.ts`: reads and writes those values as the section language has them
  (`border:2px solid #RRGGBB`); `slideShape.test.ts` covers the border text.
- The editor publishes pictures and shapes as selections too, with `kind`; an edit of what the
  server draws as a picture reads the slide again after the save (`edit(change, true)`).

## Checked
- In Chromium against a live server: a rounded rectangle's opacity, radius, dashed border and
  width, and a picture's Fit, alt text and replacement, each matched in the saved section.

## Not verified
- Not opened in PowerPoint. The mockup's picture Background, Opacity, Radius and Border, Effects
  and Advanced are not offered: a picture has no such style in the section language.

## Follow-ups
- Let a picture carry a corner radius, border and opacity in the section language and the
  compiler, then offer them.
