# The Codex cancel test waits for the turn to start instead of sleeping (shipped)

Why: `test_cancelling_a_turn_interrupts_it_in_codex` failed on Windows for #913 and #909 with only
`initialize` sent. It slept 0.5 s and then cancelled; on a slow runner the turn had not started, so
there was nothing to interrupt.

## Shipped
- `tests/test_code_runtime.py`: the test waits (up to 20 s) until the fake Codex has logged
  `turn/start`, then cancels. What it asserts is unchanged.

## Not verified
- Windows: CI's Windows `pytest` is the check. The self-wake flake seen alongside it is fixed by #910
  (c8ff6b4), not here.
