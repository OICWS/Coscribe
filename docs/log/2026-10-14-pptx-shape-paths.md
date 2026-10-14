# PowerPoint part 2, PR 1: shapes inside groups are listed and reached by path or name (shipped)

Why: a page compiles to groups (one per `<g id>`), and the shapes inside a group could not be
listed or edited: every tool took a top-level index only. A deck built from pages that the user
then changed in PowerPoint, and any deck the user brings with grouped shapes, could not be edited
inside its groups (decision 0010, editing path b).

## Shipped
- `tools/_pptx_shapes.py`: a shape is addressed by its index, by a path through groups (`"3/1"`,
  member 1 of the group at index 3) or by a name only one shape on the slide has (a deck built
  from pages names its groups after the page's `id`s). A path out of range or a name two shapes
  share says what to do instead.
- Positions are slide inches both ways: a group can scale its members (`chOff`/`chExt` against
  `off`/`ext`), so listing and moving a member go through every enclosing group's transform.
- `list_pptx_shapes`: a group's entry lists its `members`, each with its `path`, nested groups
  included; top-level entries are unchanged, so the preview's click-to-pick overlay is unaffected.
- The 13 tools that take `shape_index` take a path or a name too. `add_pptx_animation` refuses a
  member (PowerPoint animates a group as one shape) and names the group to animate instead.
- No new tool; `tests/tool_schemas.txt` changes for `list_pptx_shapes`' description.
  `tools/presentations.py` is 7 lines shorter.
- `tests/test_pptx_shape_paths.py` (12 tests, 11 fail without the change): members listed with
  paths, a scaled group placed and moved in slide inches, reached by path and by name, deleted
  from its group, wrong and shared names, the animation refusal.

## Not verified
- Windows, and a deck with groups made in PowerPoint itself (the tests build their groups with
  python-pptx, scaled by hand).
- The model using paths: measured with PR 2's edit tasks.

## Follow-ups
- PR 2: find and replace text in any shape, keeping its formatting. PR 3: the compiler names
  shapes after their page `id`.
- Under `pytest -n 4`, a different `*_survives_libreoffice_conversion` test fails now and then
  and passes alone (LibreOffice run in parallel); not this change.
