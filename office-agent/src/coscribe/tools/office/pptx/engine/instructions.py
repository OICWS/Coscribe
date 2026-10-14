"""The coordinator's paragraph that sends a new deck to the pages and `build_pptx_from_pages`.

It follows the coordinator's own instructions, whose PowerPoint part covers a user's own template
and a deck the user brings.
"""

NEW_DECK_INSTRUCTIONS = """\
A new PowerPoint deck is built from pages, whether or not the user names a style: call \
load_skill("PPTX Pages") first, write one SVG file per slide into a folder next to the deck \
with write_file, then build the deck with build_pptx_from_pages (find it with search_tools) \
and fix what it reports. Do not use write_pptx, fill_pptx_template or run_node_script for a \
new deck, and do not ask the user to pick a template for it. A deck the user already has, or \
their own template, stays on the PowerPoint tools above. To change a deck built from pages, \
edit its pages and build again.
"""
