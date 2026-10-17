# `workflows/engine.py` graph builder split (shipped)

Why: #348 item 4. `build_graph` was 285 lines and complexity 44, one function holding every node.

## Shipped
- `workflows/engine.py`: `build_graph` is now a three-line call into `_GraphBuilder`, whose methods are
  the former closures (`emit`, `fail`, `make_node`, `_permission`, `_approval`, `loop_start`,
  `loop_next`, `loop_collect`, `wire`). Bodies are unchanged; the shared names became attributes.
- `workflows/loop_labels.py`: `item_labels` and its helper moved out of `engine.py` so the file does
  not grow past its ratchet entry (922 to 901 lines).
- `quality/baseline.json`: `long_functions` 36 to 35, `complex_functions` 21 to 20, engine file lines 922 to 901.

## Not verified
- `tests/test_workflow_*.py` and `tests/web/test_scheduled.py` pass locally; no workflow was run in the
  desktop app against a real model.

## Follow-ups
- Left over 300 lines: `create_app_lg` and `_decide_action_request`.
