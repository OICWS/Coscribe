# The open conversation can be deleted (shipped)

Why: the thread menu hid Delete for the conversation you were in, so deleting it meant opening
another one first. Allen asked for Delete there too (#588, part 1).

## Shipped
- The thread menu offers Delete for the open conversation. After confirming, a new conversation
  opens and the old one is deleted.
- Deleting a conversation stops its running turn and waits for it to end
  (`ChatSessionLG.stop_and_wait`, up to 15 s). A turn still waiting on an approval would
  otherwise write a checkpoint after the delete and bring the conversation back.

## Not verified
- Clicked through only in the test client, not in the desktop app.
