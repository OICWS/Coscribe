# Five more connectors in Discover: Exa, Attio, Ramp, tl;dv, Similarweb (shipped)

Why: more office-relevant connectors that need no setup: no sign-in (Exa) or one sign-in in the
user's browser (the rest), like the current ones.

## Shipped
- `web/connector_catalog_more.py` holds the five entries (the catalog file is at its size limit);
  `connector_catalog.py` appends them. Exa needs no sign-in; the others use OAuth.
- Icons in `frontend/src/assets/connectors/` (the makers' own logos; Similarweb's was there already).
- Checked live on 2026-10-25: Exa ran a real search; Attio, Ramp, tl;dv and Similarweb registered a
  client for a `127.0.0.1` redirect address.

## Not verified
- A full browser sign-in to Attio, Ramp, tl;dv and Similarweb (needs accounts), and their tool lists:
  the servers show tools only after sign-in, so the entries list none.
- Looks of the new cards on Windows. The Attio icon is upscaled from a 32 px favicon.

## Follow-ups
- Square, Sentry, Vercel, Neon and Jam also register a client; left out as less office-relevant.
