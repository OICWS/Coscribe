# Web search and page reading fail within seconds, say why, and fall back to the provider's search (shipped)

Why: on a network that can't reach the free search engines (a country that blocks them, a proxy
whose upstream is down), `web_search` spent about 20 s per attempt, three attempts, and handed
back the last engine's error ("No results found." or a bare timeout), so neither the model nor the
person could tell what was wrong. Measured on a Windows PC in China whose proxy accepted
connections but reached nothing: every engine timed out, direct and through the proxy.

## Shipped
- `tools/web/_search.py`: each of ddgs's text engines (brave, duckduckgo, mojeek, startpage,
  yahoo, then wikipedia and grokipedia) is asked on its own, all at once, 6 s per engine and 8 s
  in all; once one answers, the others get 1 s more. Results keep that engine order, one per URL.
- When no engine could be reached, the error says so: "through the proxy <address>" (without
  its password) or "from this network", with where the proxy setting is. It is not retried, and
  the same answer comes back at once for 30 s for the same proxy. When engines answered with
  nothing, the error says that, and the search is tried once more (was three times).
- `read_web_page`: connect timeout 6 s (read stays 20 s); a failed connection says the host,
  whether a proxy was used and that the browser may still open the page.
- When the free engines fail, the search goes through the person's model provider with the key
  they already gave, where the provider has a search API of its own: which ones do is a table
  beside the model catalog (`runtime/models/web_search.json`, a source and a date per row; models.dev
  has no such field). DeepSeek only for now (`/v1/tools/search` and `/v1/tools/fetch`, $0.75 per
  1,000 successful requests, checked 2026-11-26). A page that can't be reached directly is read
  through the provider's fetch, except in a conversation limited to some sites. Collins chose free
  first and the provider only as the fallback, for every provider.
- The table is kept by hand; each row also lists the phrases its source must still say (the
  endpoint paths, the price line). The model catalog's job (1st and 15th) runs
  `scripts/check_web_search_sources.py` and opens or updates an issue when a source stopped
  saying one, so a changed price or endpoint is noticed without anyone remembering to look.
- Checked live with a real DeepSeek key behind a dead proxy: the free engines failed at once,
  DeepSeek answered a Chinese query with 3 results, and a page came back through its fetch, 5.8 s
  for both.
- In this container the new search answered 3 of 3 sample queries in 1 to 3 s; ddgs's auto mode
  answered 2 of 3.

## Not verified
- A real Windows machine behind a working and a broken proxy; the behaviour was measured there
  before the change, not after it.

## Follow-ups
- Anthropic, OpenAI and Gemini search only inside a model call (a server tool, about $10 to $14
  per 1,000 searches plus tokens): add them to the table as a second kind, used the same way.
- Show web search as a provider capability in Settings > Providers and the model picker.
