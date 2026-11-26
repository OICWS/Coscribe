# Web search and page reading fail within seconds and say why (shipped)

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
- In this container the new search answered 3 of 3 sample queries in 1 to 3 s; ddgs's auto mode
  answered 2 of 3.

## Not verified
- A real Windows machine behind a working and a broken proxy; the behaviour was measured there
  before the change, not after it.

## Follow-ups
- Search through the model provider's own web search, no extra key (`docs/plan.md`).
