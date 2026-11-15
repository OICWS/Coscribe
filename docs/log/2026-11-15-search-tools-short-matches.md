# `search_tools` sends its best three matches in full and the rest as a name and a line (shipped)

Why: a `search_tools` result carried the full description and parameter schema of up to eight
tools, 5,000 to 21,000 characters each time (`docs/log/2026-11-10-tool-search-recall.md`,
follow-up). Most of it was tools the model did not want.

## Shipped
- `runtime_lg/tool_deferral.py`: the first three matches keep their description and parameters;
  the rest come back as `{"name", "summary"}`, the summary being the description's first sentence
  (at most 160 characters, not cut at "e.g." or "i.e." in any case). The tool's description says a weaker match is
  fetched by searching its name.
- An exact tool name now ranks that tool first. It had not: `spawn_agent` returned
  `spawn_agent_background` first, so a name search could not have fetched it. The bonus also
  raises the floor of what else comes back: a search by a tool's name now returns that tool and
  few neighbours (`list_pptx_shapes` no longer lists `edit_pptx_shape`; 67 of the 98 hidden tools
  return fewer matches by name). `tests/test_tool_search_recall.py` checks that every hidden tool
  comes back first and in full by its name.
- Measured on the 89 queries of `tests/test_tool_search_recall.py` against the real catalog: the
  tool asked for was first in 65, second or third in 17, fourth or lower in 6. The results' total
  fell from 708k to 406k characters (median 7.4k to 4.2k, largest 19.8k to 10.1k). Every tool of
  the catalog comes back first and in full when searched by its name.
- `tests/tool_schemas.txt` regenerated on Python 3.11 (the description of `search_tools`
  changed).

## Measured on the agentic evaluation (`deepseek:deepseek-flash`, effort low, one run each)
DeepSeek binds every built-in tool up front (`keeps_tool_list_fixed`), so its normal run does not
search for built-in tools. The evaluation was also run with that turned off, as every other
provider runs:

| run | done | model calls | input tokens | `search_tools` calls | cost |
|---|---|---|---|---|---|
| `main`, tools found by search | 12/12 | 214 | 3,293,855 | 13 | $0.078 |
| this change, tools found by search | 12/12 | 199 | 3,171,393 | 18 | $0.076 |

Five more searches, four of them a weaker match fetched by its name (e.g. `notion`, then
`find_connector`, then `offer_connector`); no call was made with guessed arguments. Input tokens
3.7% lower. One run per side, so the difference is within the noise; the change does not make
the tasks fail. With DeepSeek's own binding the runs searched for no built-in tool and were not
compared.

## Not verified
- The token saving on the providers that search for tools (Anthropic, OpenAI, Gemini): no key
  for them here. Their cache misses cost more than DeepSeek's, so a shorter result counts for more.
- The independent review `tool_deferral.py` needs as an invariant path.
