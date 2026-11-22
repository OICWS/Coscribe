# A simple conversation view: the reply, and one status line while it works (shipped)

Why: people doing office work don't need to see each command and file read, the model's notes
between steps, or token counts. They want to know that it is working, and then the answer.

## Shipped
- Settings > General > Appearance > Conversation view: Detailed (the default, unchanged) or
  Simple, saved as `COSCRIBE_CONVERSATION_VIEW` in `.env` like the theme.
- Simple draws a turn without its tool rows and without the model's in-between words
  (`frontend/src/lib/simpleView.ts`, `components/chatlog/SimpleView.tsx`). While the turn runs,
  one line at the bottom says what it is doing, with no object, and for how long: `Thinking 3s`,
  `Running commands 12s`, `Reading`, `Writing`, `Editing`, `Searching`, `Browsing`, otherwise
  `Working`. The line is hidden while an approval, question, plan or folder card waits for the
  person, and gone when the turn ends; the reply shows then, all at once (until the turn ends,
  any text may turn out to be narration before another call).
- Every card stays: approvals, questions, plans, the task list, folder access, a refused write's
  folder card, package installs, connector offers, file cards, the stopped note, reactions. The
  composer's time and tokens and the usage ring are hidden.
- A script's approval card, in both views: the description shows once, in the card's title,
  which now wraps instead of cutting it off; the "Not isolated" note's explanation shows on
  hover over the badge instead of under it.
- Only the drawing changes: the transcript, the server and the prompt are untouched, so switching
  back to Detailed shows every step of every turn.

## Not verified
- On Windows in the desktop app. Checked in a browser against a local server with a real model
  (DeepSeek `deepseek-flash`): one office task of 19 steps showed Thinking, Running commands,
  Editing, Writing and Reading in turn, three script approvals with the line hidden, and the reply
  at the end.

## Follow-ups
- None planned; whether office users want it on by default is for the maintainer to judge from use.
