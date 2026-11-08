# 0040: A task starts on an event another program on the machine sends

Status: proposed (2026-11-08, OICWS; agreed with the maintainer in the project thread). Narrows
0034 and follows 0039 (a task may start on an event sent to it). Part of #843.

## Context
A script, a Power Automate Desktop flow, an Excel macro or a team's own tool knows when something
happened and could tell a task, but the server listens on a new port each launch and refuses a
request without the launch token, so nothing outside the window can start a run.

## Decision
- **A new trigger kind, `webhook`**: a program POSTs JSON (at most 64 KB) to
  `http://127.0.0.1:<port>/hooks/<task id>` with `Authorization: Bearer <key>`, and each event
  starts one run. Its inputs come from the event as a connector item's do (0039).
- **A listener of its own**: 127.0.0.1 only, on a fixed port (8765, `COSCRIBE_WEBHOOK_PORT`),
  started while a webhook task is on and stopped when none is. It answers that one route and
  nothing else, so the main server's guard stays as it is. A busy port is shown on the task.
- **A key per task**: 32 random bytes in the keychain (the plaintext fallback of other secrets
  where there is none); the listener checks a SHA-256 of it, in constant time. The task page shows
  it and makes a new one. A wrong key and an unknown task get the same 401. A request with an
  `Origin` header is refused, so a web page in a browser cannot send one.
- **Answers**: 202 with the run, 400 with why the event can't fill the inputs, 409 for a paused
  task, 429 over the limits (3 runs going, 30 an hour, 1 to 120 by the task). A refused event is
  not kept to retry: the sender sees why and may send it again. Each event is in the audit log
  (`webhook_event`: size and outcome, never the body); a refused one is listed on the task.
- **A sample first**: "Wait for a sample" keeps the next event without running it, so the form
  can show its fields to map to inputs.
- **Only the person turns it on**, in the task form, for a task with steps. The event is outside
  content; the run keeps the task's autonomy and permissions.

## Consequences
- Runs started this way say "Webhook" and keep the event under Details.
- Out of scope: internet webhooks (no listener off 127.0.0.1), signed bodies, a queue for events
  over the limits.
