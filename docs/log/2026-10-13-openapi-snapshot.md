# The HTTP API is snapshotted as an OpenAPI document (shipped)

Why: issue #148. `tests/web_routes.txt` pins which routes exist, not what they accept and return. The frontend depends on those shapes and the server splits (#145, #146) move the code that defines them, so a change to a request or response model should be a readable diff in the PR that makes it.

## Shipped
- `office-agent/tests/test_openapi_snapshot.py` builds the app as `test_web_routes.py` does and compares `app.openapi()`, written as indented JSON with sorted keys, with `office-agent/tests/openapi.json` (125 KB, under the 200 KB size limit). `UPDATE_SNAPSHOTS=1` rewrites it.
- Deterministic without normalising anything: the same bytes with different `PYTHONHASHSEED`, temp directories and working directories. Keys are sorted because dict order follows registration order, which a file split changes without changing the API.
- Shown to fail: adding a field to `ConfigUpdate` fails the test with the new property in the diff; reverting it passes.

## Not verified
- On Windows: the file is written with `\n` and compared as bytes; the nightly Windows job runs the test.

## Follow-ups
- Generating the frontend types from the document (out of scope for #148); WebSocket messages are not in OpenAPI.
