# A wake no longer fires on a signal sent just before it (shipped)

Why: issue #161. The Windows nightly of 2026-10-13 failed `test_signal_event_before_wake_registered_does_not_retroactively_fire_it`. `SignalStore.fired_since` compared ISO timestamps with `>=`; Windows' coarse clock gave the signal and the wake the same timestamp, so a signal sent before `wake_on_event` counted as sent after it. In the product, a wake could fire on an old signal.

## Shipped
- `tools/selfwake.py`: signals and wakes take a number from one counter per state dir (`selfwake_seq.json`, bumped under a lock file). `fired_since` compares `signal.seq > wake.seq`, so the order no longer depends on the clock. A plain `>` on timestamps was rejected: a signal sent in the same tick right after the wake would be lost.
- Records saved before the counter existed have no `seq`; those fall back to the old timestamp comparison.
- Tests with a frozen clock for both orders (signal then wake: not fired; wake then signal: fired), plus the legacy fallback. Checked by making `fired_since` ignore `seq` (back to `>=` on timestamps): the signal-then-wake test fails. Wake-then-signal passes either way; it guards against the strict-`>` alternative.

## Not verified
- Windows itself: the cause was read from the code and reproduced on Linux with a frozen clock. The next Windows nightly must show the original test green.
