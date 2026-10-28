# The Doc's comment button matches a deck's, and the bar over selected words follows a scroll (shipped)

Why: the maintainer saw two things in the Doc panel. Its header had a bare icon where a deck has the
comment button with its options menu, and after selecting words and scrolling the page, the bar
stayed where it was drawn, above the selection's old place.

## Shipped
- `PanelCommentButton` (`components/artifacts/`) is the one comment control of a panel's header, used
  by Slides and Docs. The Docs one keeps its dot for open comments; its menu has "Show all comments".
- The bar over selected words is told which element scrolls (`data-doc-scroll`): Tiptap's bubble menu
  listens to `window` unless given another target, and the page scrolls inside its own box.
- `tests/e2e/doc-editor.spec.ts`: the bar keeps its distance from the selection through a scroll; the
  header has the comment control.

## Not verified
- The desktop app; the maintainer's own document (long, Chinese text with a callout).
