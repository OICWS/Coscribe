# Deck engine, part 2b: the build tool, its instructions, and an `engine` route in the evaluation (shipped, not offered to users yet)

Why: the engine (decision 0010) has to be usable by the agent before it can be measured against
today's route; until the measurement says so, nothing in the product tells the agent to use it
(issue #198, PR 2 of 4).

## Shipped
- `build_pptx_from_pages(pages_dir, path, sources, replace_changes)`: one new deferred tool
  (decision 0001 allows two at most). It builds the .pptx from a folder of SVG pages with
  `build_deck`, checks it, and returns per-page errors and warnings. Its description is the page
  contract. Pages are written and read back with the file tools the agent already has, so no
  second tool is needed. A deck changed after its build is refused with the way out named (the
  edit_pptx_* tools, or the user's consent to `replace_changes`). Images are taken from the
  workspace, or from the trusted folder the pages are in. It is registered from
  `tools/office/pptx/` (its `build_presentation_tools` adds it to today's tools), so
  `tools/presentations.py`, held at its size by the ratchet, and `coordinator.py` are unchanged.
  `tests/tool_schemas.txt` gains the tool;
  `search_tools`' description changes once (its group count).
- `tools/office/pptx/engine/guide/`: `SKILL.md` ("PPTX Pages": the workflow, layout by content
  relationship, type and colour, charts drawn to scale, an avoid list; condensed in part from
  ppt-master's MIT design references, with credit) and `instructions.md` (the paragraph that would
  replace today's PowerPoint guidance for new decks). Neither is loaded by the product yet.
- `evals/run.py --route engine`: each task's session gets the skill in its own skills folder,
  "PPTX Slides" switched off, and the paragraph after the coordinator's instructions, so the route
  is measured as it would ship.
- `tests/test_deck_engine_tool.py` (11 tests): a page using everything the description allows
  compiles without an error (this test found that the emitter rejects `scale()` on a group that
  holds text, and the contract now says translate only); path rules; the refusal; the route
  installs and removes its instructions; the instructions name the skill and the tool that exist.

- One task end to end on the engine route (01-q3-review, deepseek-flash, effort low, off-peak):
  the agent loaded the skill, wrote 6 pages, built and repaired them; all 19 facts present, 6
  pages, every slide titled and listable, no overflow or overlap, and a clean, consistent deck to
  the eye. It cost 0.043 dollars (about 0.29 yuan at the Chinese page's prices) and 334 s, against
  0.025 and 183 s for today's route on the same task in the baseline. Of its 55k output tokens 38k
  were reasoning over 26 model calls; the pages themselves are about 17k. The round trips were
  the waste (5 builds, 5 renders, 7 small edits for 6 pages), so the guide now says to write each
  page once, build once and look once. `evals/prices.py` now says its prices are dollars.

## Not verified
- Windows.
- The guide's write-once wording was not run again here; the measurement on all ten tasks is the
  next PR and shows whether it lowers the cost.

## Follow-ups
- #198: the measurement against the baseline; only if it wins, the instructions switch.
