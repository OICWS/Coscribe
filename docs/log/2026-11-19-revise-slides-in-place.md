# Revise SVG-based PowerPoint decks in place (shipped)

A requested revision could leave extra PPTX files when rebuilding over the
current file was refused after a direct PowerPoint edit.

## Shipped

- The coordinator and PPTX Pages skill direct revisions to the existing
  source pages and PPTX path. An explicitly requested version gets its own
  file and source pages.
- On a rebuild conflict, the builder directs the agent to edit the existing
  PPTX if it can preserve the edits there, or ask before replacing them.
  Building elsewhere and moving or copying the result over the original
  would replace those edits too.
- Tests cover two revisions to one file, a separate build, and refusal to
  overwrite an edited file without the existing explicit override.

## Not verified

- Live model adherence to the updated instructions. The conflict check is
  enforced by the builder. The choice of output path follows the instructions.

## Follow-ups

- None.
