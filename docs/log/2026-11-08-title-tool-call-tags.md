# A conversation's auto title is never a tool-call tag (shipped)

Why: while testing with DeepSeek, a conversation's sidebar title came out as the literal `<tool_call>`. The side model sometimes answers the title request with a tool call or its reasoning written out as text, and `clean_title` kept the reply's first line whatever it held.

## Shipped
- `conversation/turn_text.py`, `clean_title`: drops `<think>`/`<thinking>`/`<reasoning>` blocks (an unclosed one to the end), cuts the reply at the first tool-call marker (`<tool_call>`, `<function_call>`, `<invoke>`, DeepSeek's `<｜tool▁calls▁begin｜>` and the like), and strips any other bare tag or `<｜…｜>` token. A reply left empty, or one that is only a JSON object or list, gives no title.
- No title means what a failed title call already meant: the first message stays the label, and the end of the first turn asks again with the reply. A title written before a tool call ("Q3 销售汇总\n<tool_call>…") is kept.
- Tests: `tests/test_title_length.py` (a bare tag, a tool call with its JSON, DeepSeek's tokens, a title before a call, reasoning around the title, a comparison like `a < b` that is not markup).

## Not verified
- A live DeepSeek run that reproduces the tag; the cases are taken from the formats DeepSeek and other models write.
- Titles already saved as `<tool_call>` stay until renamed; the fix only applies to new titles.
