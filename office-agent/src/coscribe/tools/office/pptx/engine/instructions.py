"""The coordinator's paragraph that sends a new deck to the pages and `build_pptx_from_pages`.

It follows the coordinator's own instructions, which still describe `write_pptx` and the templates
for a user's template and a deck the user brings, so it says what it replaces.
"""

NEW_DECK_INSTRUCTIONS = """\
New PowerPoint decks are built from pages: this replaces the guidance above for any NEW deck \
the user asks for, whether or not they name a style. Call load_skill("PPTX Pages") first, \
write one SVG file per slide into a folder next to the deck with write_file, then build the \
deck with build_pptx_from_pages (find it with search_tools) and fix what it reports. Do not \
ask the user to pick one of the templates listed below, and do not use write_pptx, \
fill_pptx_template or run_node_script for a new deck. The rest of the PowerPoint guidance \
above still holds for a deck the user already has or their own template: edit it with \
edit_pptx_text, duplicate_pptx_slide and the other edit_pptx_* tools, or fill it with \
fill_pptx_template. To change a deck built from pages, edit its pages and build again.
"""
