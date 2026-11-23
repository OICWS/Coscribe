# Backend lifecycle and file handling (shipped)

Review issues #1041 and #1042 identified cases where work could repeat after a restart,
a deleted conversation could wake, or concurrent writers could replace an output.

## Shipped

- Startup keeps nested checkpoints for existing runs. Active runs keep their task record and stop control.
- Deleting a conversation cancels its pending wakes. Each chat tab pages through compacted history independently.
- Office conversions and artifact copies preserve competing output files. An HTML artifact owns its dashboard data folder only when its page carries the dashboard marker.
- Conversation state paths are checked using Windows filename rules on every platform.
- Python and npm package installs keep the server's full environment, so a company mirror, registry or proxy set in environment variables still applies. Python setup retries an interrupted baseline install, and chat checks installed Python versions against the requested constraint.
- HTTP responses mask secrets before applying the display limit.

## Not verified

- Running Office or WPS interactively on Windows and sending a real Dashboard to the Windows recycle bin.
