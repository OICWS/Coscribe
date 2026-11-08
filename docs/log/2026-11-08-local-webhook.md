# A task starts on an event a program on the machine sends (shipped)

Why: a script, a Power Automate Desktop flow or an Excel macro knows when something happened, but
nothing outside the window could start a run (#850, part of #843; decision 0040).

## Shipped
- A new kind in the task form, "When a program sends it an event": at most how many runs an hour
  and which input each event's fields fill (`WebhookTriggerFields.tsx`). The task page and the
  form of a saved task show the address and the key with Copy, a new key, a PowerShell line to
  paste and "Wait for a sample", which keeps the next event without running it so its fields can
  be picked (`WebhookAddress.tsx`).
- The listener is its own small server on 127.0.0.1 and a fixed port (8765, Settings > Sessions),
  on only while a webhook task is on (`web/webhook_listener.py`). It answers `POST /hooks/<task
  id>` and nothing else: 401 for a wrong key or an unknown task alike, 403 for a request with an
  `Origin` header, 409 for a paused task, 413 over 64 KB, 415 for a body that isn't JSON, 400
  with why an event can't fill the inputs, 429 over the limits, 202 with the run.
- The key is 32 random bytes in the keychain; its SHA-256 is what an event is checked against,
  and only that hash and the keychain reference are on disk (`tools/bookkeeping/
  webhook_events.py`). Each event with the task's key goes to the audit log (`webhook_event`,
  size and outcome, never the body).
- Validation of a connector or webhook rule moved to `tools/bookkeeping/event_rules.py`; the agent
  cannot switch a task to either kind. A run started this way says "Webhook" and keeps the event
  under Details.
- Tests: `tests/web/test_webhook.py` (through the listener's real socket), and the e2e
  `workflow-webhook-trigger.spec.ts`.

## Not verified
- A program on Windows sending to it (PowerShell, Power Automate Desktop), and the port setting
  in the desktop app.
