# coscribe frontend

The React + TypeScript UI of coscribe, built with Vite into the server's static folder
(`../src/coscribe/web/static/`, gitignored). What lives where, the wire contract and the rules for
changing it are on the card: [`AGENTS.md`](AGENTS.md).

## Dev loop

```sh
npm install
npm run dev        # Vite on http://127.0.0.1:5173/static/
```

Vite proxies `/api/*` and `/ws/*` to a running `coscribe-web` (default `http://127.0.0.1:8000`,
`COSCRIBE_BACKEND` to change it). Start both with the same `COSCRIBE_LAUNCH_TOKEN` when the
backend asks for one: the Vite page has none of its own, so Vite adds it to what it proxies.

## Checks

```sh
npm run build      # tsc -b and the Vite build; a change must pass this, not only tsc --noEmit
npm run lint       # oxlint
npm test           # vitest, the unit tests next to their files
npm run test:e2e   # Playwright specs in tests/e2e, against a live backend
```

The WebSocket types in `src/types/wire.gen.ts` are generated from `conversation/wire.py` by
`python scripts/gen_wire_ts.py`; never edit that file by hand. `bash scripts/check.sh --fast` in
`office-agent/` runs the build and the linters with the backend's checks.
