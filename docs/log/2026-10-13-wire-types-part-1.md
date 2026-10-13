# Typed WebSocket events and a conformance check (partly shipped)

Why: issue #163. The HTTP API is pinned by `tests/openapi.json`; the chat WebSocket was not. The server sends plain dicts and `frontend/src/types/wire.ts` is written by hand, so a renamed field broke the UI silently.

## Shipped
- `conversation/wire.py`: one `TypedDict` per server-to-client event (27 types, read from every `send_json` and `_send_live` call, including the approval, scheduled-run and workflow paths) and per client-to-server message (11 types, from `web/routes/ws.py`; `question_response` has three shapes). Stdlib only. `SERVER_EVENTS` and `CLIENT_MESSAGES` map each `type` to its TypedDicts.
- `tests/wire_check.py`: a small validator over those TypedDicts (unknown `type`, missing key, extra key, wrong value type all fail). Hand-rolled because pydantic's `TypeAdapter` refuses `typing.TypedDict` on Python 3.11.
- Every payload sent during the test run is checked: an autouse fixture in `tests/conftest.py` wraps Starlette's `WebSocket.send_json` (the browser panel's `/ws/browser` excepted), and the fake sinks in five test files call `check_event`.
- `tests/test_wire.py`: the validator's own cases, and a check that the `type` literals in `wire.ts` equal the ones in `wire.py`.
- Where `wire.ts` and the Python disagreed, the Python is what is typed: `connector_tools` and `reviewer_note` are always sent (`wire.ts` has them optional); a workflow step record always carries `note`, `iteration` and `permission` (optional in `wire.ts`); a `steer` history entry can carry `images` (not in `wire.ts`); the sub-agent forward of `approval_required` is the only sender of `subagent_id` and `subagent`.

## Not verified
- Events that no test reaches are typed from reading the code, not from a run.
- The TypeScript is not generated yet (part 2, so `wire.ts` is unchanged).

## Follow-ups
- Part 2: generate `frontend/src/types/wire.gen.ts` from `wire.py` and check it in a test.
