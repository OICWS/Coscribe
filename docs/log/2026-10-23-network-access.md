# Edit environment > Network: none, limited to listed domains, or full (shipped)

Why: issue #560, part 5. A conversation's reach to the internet was not a setting: the web tools
went anywhere and an isolated script always had the network. Allen chose three levels: None,
Limited (allowed domains) and Full.

## Shipped
- `runtime/network_access.py`: `NetworkAccess` keeps `{mode, domains}` per conversation in
  `<thread>.network.json` (removed with the conversation); the default is `limited` with `*`.
  A domain covers its subdomains; `https://www.Example.com/a` and `*.example.com` are stored as
  `example.com`. `NetworkGuard` applies it and is read at each call, so a change reaches the next
  step of a running turn.
- None: `web_search`, `read_web_page`, the image tools, `http_request` and every browser step are
  refused with a message that names Edit environment > Network. Limited: `read_web_page`,
  `download_image` and `http_request` reach only the listed domains, checked on every request
  through an httpx hook, so a redirect off the list is refused too; searching still works (it
  reaches only the search engine). Full: everything.
- Scripts in the container get the network only with Full (`Isolation.network`); the container
  can only grant the network whole, so Limited means offline. The script tools say so.
- The browser panel: the backend sends the list with each step as `network_sites`, and the
  desktop app checks the site of every step against it (`browserAgent.ts`), and again where the
  step ended up, as a redirect or a clicked link can leave the list: such a page is replaced by a
  blank one and the step fails, so its content never reaches the model (the backend checks the
  returned tab too). No site permission widens it.
- `GET`/`PUT /api/threads/{id}/network`; a change is written to the audit log as
  `set_network_access`.
- Edit environment > **Network**: the three options and, for Limited, the allowed domains, one
  per line. The summary row shows the level.

## Not verified
- The desktop app's check on a real Windows machine (the Python side is tested with a fake host).
- Live with DeepSeek on Linux: in a conversation limited to example.com, `read_web_page` on
  python.org was refused with the message, and example.com was read.

## Follow-ups
- Connectors and the code module are not under this setting (the page says so for connectors).
- A script that runs without isolation keeps the network (the page says so).
