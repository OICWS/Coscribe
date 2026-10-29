# Export a conversation as one Markdown file (shipped)

Why: the maintainer asked how to send a whole conversation for a bug report (a turn that seemed
stuck, a Word file that kept being fixed). The only way was the checkpoint database.

## Shipped
- The conversation menu in the sidebar has "Export conversation". It saves
  `conversation-<id>.md`: every message in order, and every tool call with its arguments, its
  result and whether it failed. Arguments and results over 1,500 characters are shortened.
- `GET /api/threads/{thread_id}/export` returns that file (a read; audited in
  `tests/web/test_launch_token.py`).

## Not verified
- The save in the desktop app on Windows (the browser's download path is the one the Slides
  export already uses).
