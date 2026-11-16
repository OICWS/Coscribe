# `search_tools` finds a hidden tool from the words a model asks with (shipped)

Why: about 100 tools are hidden behind `search_tools` (decision 0001). The search matched a
query's exact words against tool names and descriptions, and names are literal (`write_pptx`).
A tool that is not found does not exist for the model. Row "search_tools recall" of the
engineering assessment of 2026-11-09; part of #867.

## Shipped
- Measured first, on the real catalog. 52 queries in a model's words ("powerpoint",
  "spreadsheet", "make slides", "javascript", "memory", "生成PPT"): the tool was among the results
  for 32, and first for 24. 20 found nothing or the wrong thing; every Chinese query found
  nothing, because only Latin letters were read.
- `runtime_lg/search_words.py`: plurals fold ("slides" finds "slide"), and a query gains the
  catalog's word for its own (powerpoint, deck: pptx; spreadsheet, excel: xlsx; javascript: node;
  about 40 English words and 24 Chinese phrases). In `tool_deferral.py` the score also prefers,
  among names holding the same query words, the name that is little else (`write_pptx` before
  `add_pptx_shape_effect`).
- After: 51 of the 52 found, 36 first (the one miss, "skill", is a tool the test catalog does
  not hold). A second list of 38 queries, written after the table and without looking at it:
  34 found, 26 first (before the change 29 and 22). Three of its four misses then got their
  words in the table; "word to pdf" still misses and is kept in the test as a known miss.
- `tests/test_tool_search_recall.py` holds both lists against the real catalog (88 queries).
- What the model is sent did not change: `search_tools` keeps its name, parameters and
  description, so `tests/tool_schemas.txt` is the same.

## Not verified
- A real model's own queries: the lists are what the author expects a model to write. The turn
  record (`turns.jsonl`) does not keep queries; the first sample of real ones should be added
  to the test.
- Connector tools: the table's words are the built-in catalog's. "document" now also finds the
  `docx` tools beside a connector's own document tools.

## Follow-ups
- A result carries the full description and parameters of up to 8 tools: 5,000 to 21,000
  characters for the queries above. Returning the best three in full and the rest as a name and
  one line would cut most of it; that changes what the model reads, so it needs the agentic
  evaluation run before and after.
- An independent review, since `tool_deferral.py` is an invariant path.
