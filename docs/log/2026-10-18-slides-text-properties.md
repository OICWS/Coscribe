# Text box properties panel (part 2 of the properties panel)

Why: selecting a text box shows its properties in the right-hand panel, with the deck's named text
styles and palette (decision 0017), in place of the format bar's few presets.

## Shipped
- `SlideProperties` shows the selected text's properties when a text element is selected in the
  editor, else the slide's transition and background as before. The editor publishes its selection
  (`SlideEditor.tsx`, `usePublishedSelection`); an edit from the panel ends typing, then changes
  the element in the editor's section, which draws and saves it like any other change.
- `SlideTextProperties.tsx`: Layout (padding); Text (text style, font, weight, size, line height
  and letter spacing, colour, italic and underline, list kind, alignment); Appearance (background).
  Text style, font and colours come from `design-system.json` (`useDesignSystem.ts`); the colour
  picker's Theme tab lists the deck's palette.
- `lib/slideText.ts`: reads a text element's values and writes them back as the section language
  has them. Choosing a style writes its values and `data-text-style`; changing the size, weight,
  font, line height or letter spacing by hand takes the mark off ("Custom").
- The design system's fonts are also read from SVG `font-family` attributes (decks coscribe wrote).

## Checked
- In Chromium against a live server on a six-slide deck: Heading 3 written to the section with its
  size, weight, line height and mark; a hand-set size dropped the mark; font, weight, line height,
  letter spacing, padding, italic, underline, centring, both colours and bulleted and numbered
  lists each changed the section as expected and were saved (HTTP 200).

## Not verified
- Not opened in PowerPoint. Case, Resize (shrink text to fit), Opacity, Radius, Border, Effects
  and Advanced of the mockup are not offered: the section language has no style for them on text,
  so they would not reach the .pptx.
- The format bar still has its own five presets (Title, Heading, Lead, Body, Caption), which do
  not know the deck's styles; the panel shows "Custom" for text set by them.

## Follow-ups
- Retire the bar's presets in favour of the deck's text styles.
- Tables, pictures and shapes get their own panels; Effects and Advanced follow once the section
  language can carry them.
