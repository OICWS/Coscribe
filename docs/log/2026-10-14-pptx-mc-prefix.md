# Slide transitions write `mc:Ignorable` under the `mc` prefix (shipped)

Why: `set_pptx_transition` set the markup-compatibility `Ignorable` attribute on the slide root
without a declared prefix, so lxml wrote it as `ns0` (#174). PowerPoint writes `mc:`, and the
generated name depends on what else the root declares, the same fragility the `p14:media` prefix
had before the audio goldens.

## Shipped
- `_mark_mce_ignorable` (`tools/presentations.py`) registers `mc` for the namespace before it sets
  the attribute; the file keeps its line count (the ratchet holds it).
- The `transition_and_animation` golden changes `xmlns:ns0` / `ns0:Ignorable` to `mc` and
  nothing else. Without the registration that golden fails with the `ns0` spelling, and so does
  the formula test, which now checks the saved slide XML for `mc:Ignorable="a14"`.
- The registration is lxml's process-wide prefix table: once a slide tool has run, any other
  writer that sets an attribute in this namespace with no prefix in scope also gets `mc:`. The
  docx writer's root always declares `mc` (python-docx's template does), so no file changes.

## Not verified
- Opening the deck in PowerPoint on Windows (the XML is the spelling PowerPoint writes).

## Follow-ups
- A deck coscribe saved before this change keeps its `xmlns:ns0` declaration: lxml reuses a
  prefix already declared on the root. Both spellings are valid XML; renaming it would mean
  re-serializing the slide, not worth it for a prefix name.
