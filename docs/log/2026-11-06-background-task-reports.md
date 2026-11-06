# A background script's or command's end comes back to its conversation by itself (shipped)

Why: the maintainer said background tasks don't feel smart. A background sub-agent reports to its conversation when it ends, but a background script or command only refreshed the panel. The model heard about it only if it had ended its turn with `wake_on_task`. Often it said "I'll tell you when it's done" and nothing followed. The 2026-10-29 change only told it not to poll.

## Shipped
- When a background script or command ends, its conversation gets a turn of its own. The turn names the task, says how it ended (finished, failed with its exit code, timed out, stopped by the user, cut off when coscribe closed) and gives the last 6 kB of its output. This also covers a command the person moved to the background, and one the person stopped in the panel. It runs after the turn in progress, under the same cap of report turns in a row as sub-agent reports (`conversation/subagents.py`, `_report` now serves both).
- No report is sent when the model already knows how the task ended: it read the outcome with `check_background_task`, or stopped the task with `kill_background_task` (`BackgroundTask.reported`).
- `wake_on_task` is removed, as the sub-agent one was earlier. A wake on a task still pending on disk is taken by the report, and its reason goes with it. The tool results and descriptions tell the model the end comes to it on its own.
- The chat shows the report as a card like a sub-agent's: "Background task finished" or "Background task ended" with Failed (exit N), Timed out or Stopped by you, and the output when opened.

## Not verified
- A real model on a long script. The report path is tested with a stand-in conversation, and the tools with real scripts.
- A real Windows run, including a contained script handed to the background.
- A server restart while a task runs still loses its report. The record turns `interrupted` and nothing tells the conversation, as before.

## Follow-ups
- A task that ends during the turn that started it is reported only after that turn. Telling the model mid-turn would need a notice channel of its own.
