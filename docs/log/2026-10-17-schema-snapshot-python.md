# The tool-schema snapshot test is skipped on Python 3.13 (shipped)

Why: #252. The test failed in cloud containers (Python 3.13) and passed in CI (3.11). Python 3.13
strips the indentation from docstrings, so each tool's description hashes differently.

## Shipped
- `tests/test_tool_schema_snapshot.py`: `skipif(sys.version_info >= (3, 13))` with the reason. The full
  suite in the container went from 1 failed to 0 failed.

## Not verified
- Windows ran the test on the maintainer's side (passes, per #252).

## Follow-ups
- When CI moves to Python 3.13, regenerate `tests/tool_schemas.txt` and drop the skip.
