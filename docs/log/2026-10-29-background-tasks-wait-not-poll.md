# A background task tells the model to wait for it, not poll it (shipped)

Why: the maintainer moved a command to the background, and the next few seconds showed
"Checked a background task" four times. The tool results told the model to "read its output
with check_background_task", and the model did that in a loop. Being resumed when the task
finishes (`wake_on_task`) already existed.

## Shipped
- A command the person moves to the background, a started background script or command, and a
  check on a task still running each tell the model the same thing: go on with other work, or end
  the turn with `wake_on_task` and be resumed when the task finishes; don't check again and again.
  The text is in the tool result, not in a tool's description (decision 0001).

## Not measured
- How often a real model polls now. Not measured on DeepSeek; the text only steers it.
- A task that finishes while the same turn is still running is not announced to the model
  mid-turn. That would need a notice channel of its own, not the person's steer notes.
