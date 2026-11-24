---
title: Work in a conversation
description: Send messages and files, add to a request while Coscribe works, stop it, and take back or change what you sent.
---

Everything in Coscribe starts in a conversation. Each one keeps its own history, model, permission mode and folders.

## Send messages and files

Type in the message box and press <kbd>Enter</kbd>. To attach a file or a picture, click **+** at the bottom left of the message box or drag it into the window. Attached files are saved in the workspace's `.coscribe/uploads/` folder, so Coscribe can open them again later.

## Add to a request while it works

You don't have to wait for a reply to finish. Anything you send while Coscribe is working becomes a note it reads before its next step, pictures and files included. A waiting note has its own buttons:

- **Send now** sends it at once.
- **Cancel and edit message** takes it back into the message box. This is only possible while the message box is empty.

When Coscribe is waiting on a card (a question or an approval), what you type answers that card instead: a typed reply to a question is your answer, and a typed reply to an approval denies the action and tells Coscribe why.

## Stop a reply

Click **Stop** at the right of the message box. Whatever Coscribe already wrote and did is kept, and the reply ends with "Stopped · What should I do instead?". It won't pick the stopped work up again unless you ask.

Stopping a reply does not stop scripts or commands it left running in the background; the line under the reply says how many are still running and opens the **Background tasks** panel, where you can stop them.

## Rewind or edit a message

Hover over a message you sent to see when you sent it and three buttons:

- **Rewind to here** removes that message and everything after it, and puts its text back in the message box.
- **Edit** lets you change the message; **Save** removes the later turns and sends the new text.
- **Copy** copies the text.

> [!WARNING]
> Rewinding removes turns from the conversation, not their effects. A file Coscribe wrote, a command it ran or a message it sent through a connector stays as it is. The tooltip warns you when a turn you are about to remove did any of these.

Rewind and Edit are not available while a reply is running or a card is waiting for you, nor for messages from before a `/compact`.

## Copy a conversation

Type `/fork` to copy the conversation into a new one and open it; `/fork Q3 draft B` names the copy. Both conversations go on from the same point and work on the same files, so a file changed from one is changed for the other.

## Keep a long conversation going

Each model can only read so much at a time. When a conversation gets long, type `/compact`: Coscribe summarizes it to free room and carries on. `/clear` archives the conversation and starts a new one in the same workspace.

## Ask a side question

The **Side chat** panel (the two speech bubbles in the toolbar) answers questions about the conversation without adding anything to it, even while a reply is running. It sees the conversation as it is right now. Its messages are kept only while the panel is open.

## Simple or detailed view

By default a conversation shows every step Coscribe takes. In **Settings › General**, set **Conversation view** to **Simple** to see only the reply and one line saying what Coscribe is doing, such as "Reading" or "Running commands". Cards that need you, such as approvals and questions, show in both views, and switching back to **Detailed** shows every step again.
