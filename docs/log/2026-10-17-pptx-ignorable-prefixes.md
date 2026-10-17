# PowerPoint asked to repair every slide with a transition: Ignorable prefixes now declared on the root (shipped)

Why: the maintainer opened a deck with a Morph transition in PowerPoint on Windows and got "PowerPoint
found a problem with content… Repair". A deck with build-ins only opened cleanly; the two decks with
Morph did not.

## Cause
`set_slide_transition` writes `p14:dur` (and for Morph a `p159:morph` effect) and lists the
prefixes in `mc:Ignorable` on the `<p:sld>` root. The prefixes were declared only on the
`<p:transition>` child. Markup compatibility resolves an Ignorable prefix where the attribute is,
so the root named prefixes that were not in scope there. Our schema check resolves prefixes
anywhere in the tree, so it passed; PowerPoint does not.

Every transition writes `p14:dur`, so every slide that `set_pptx_transition` gave a transition was
affected, not only Morph. `add_pptx_formula` (`a14`) goes through the same function.

## Shipped
- `mark_mce_ignorable` (`tools/office/pptx/transitions.py`) also declares the prefix on the root,
  with `lxml.etree.cleanup_namespaces(top_nsmap=...)`, keeping the root's other declarations.
- `tests/tools/office/pptx/test_transitions.py`: every Ignorable prefix is declared on the saved
  slide's root. The test fails without the fix.
- The `transition_and_animation` golden: `xmlns:p14` moves from `<p:transition>` to `<p:sld>`.

## Checked on Windows (the maintainer, PowerPoint, 2026-10-17)
- Four slides with no transition, Morph, Push and Fade open without a repair prompt, and each
  transition plays.

## Not verified
- A formula (`add_pptx_formula`, `a14`) opened in PowerPoint after the fix.
