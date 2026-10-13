# The frontend's wire types are generated from Python (shipped)

Why: issue #163, part 2. Part 1 made `conversation/wire.py` the checked description of every chat WebSocket message; `wire.ts` was still written by hand beside it.

## Shipped
- `scripts/gen_wire_ts.py` writes `frontend/src/types/wire.gen.ts` (about 500 lines, 50 interfaces and 4 unions) from `wire.py`; a TypedDict's docstring and the `#` lines above a field become TS doc comments. `--check` exits 1 when the file is stale.
- `frontend/src/types/wire.ts` is now a re-export of the generated types plus the `WsServerEvent` / `WsClientMessage` aliases, so no component's import changed.
- `tests/test_wire_ts.py` fails when the checked-in file differs from the generator's output (Python only, no node) and says which command regenerates it; it also checks that every message class gets an interface and that a type without a TypeScript form is refused.
- `tsc -b` against the generated types found one drift, a type-only one: `reducer.test.ts` built `approval_required` events without `reviewer_note`, which the server always sends. The test that exercises an older server that omits it now casts; the other event gets the field.

## Not verified
- Nothing runs the generated types against a live server; that is what part 1's payload check covers on the Python side.

## Follow-ups
- None.
