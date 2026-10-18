# The event-loop test no longer bounds wall-clock time (shipped)

Why: the Windows night of 2026-10-18 was red (run 29): `tests/web/test_scheduled.py::test_script_env_package_install_does_not_block_the_event_loop` measured 0.84 s against its 0.4 s bound on the runner. `office-agent/CLAUDE.md` says not to assert on elapsed time.

## Shipped
- The slow install now blocks on a `threading.Event` instead of `time.sleep(0.5)`. The test waits until it has started, makes an unrelated request, and only then releases it; it asserts the install was still waiting when that request finished. No bound on seconds.
- Checked by breaking: calling `install_package` inline in the `async` handler (no `asyncio.to_thread`) makes the test fail, because the loop is blocked until the install's 3 s wait times out.

## Not verified
- Windows itself: the next scheduled Windows run is the check. The clock for 14 green nights restarts from the next green night.
