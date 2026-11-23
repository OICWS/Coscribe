---
title: Approvals and permission modes
description: Choose how much coscribe may do on its own, and answer the cards it shows when it needs you.
---

coscribe does nothing outside its reach without your say. How often it asks depends on the conversation's permission mode; what it can reach at all depends on the [workspace](../workspaces/workspaces.md).

## The four modes

Pick a mode with the mode button below the message box. The default for new conversations is set under **Settings › General › Default mode**.

| Mode | What it does |
|---|---|
| **Manual** | Asks before every change, script or outside action. |
| **Accept Edits** | Edits files in your folders without asking; still asks before running code or outside actions. |
| **Plan** | Researches and writes a plan for you to approve before any change. See [Plans and task lists](plans.md). |
| **Auto** | A reviewer model approves routine actions and blocks risky ones instead of asking you. |

If you switch modes while a reply is running, the new mode takes effect when the reply ends.

## Approve an action

When coscribe needs your approval, a card in the conversation names the action, such as "Run a command", and shows what it will do: the file it will write, the script or the command. Read it, then choose:

- **Approve** lets this one action go ahead.
- **Allow for this task** (shown for the code module's commands and changes) lets the same kind of action go ahead for the rest of the task without asking again.
- **Deny** refuses it. To say why, type your reason in the message box instead; coscribe reads it and adjusts.

If the card has scrolled out of sight, a notice above the message box says something is waiting; **Show** brings you back to it.

> [!IMPORTANT]
> A script's card says how it will run. Normally a script runs isolated: it can use only the conversation's folders, can't delete or rename files there, and reaches the internet only when the workspace's **Sites** setting is **Any site**. A **Not isolated** badge means the script will run without that isolation and can reach any file you can; hover over the badge to see why, and read the script before you approve.

## Give access to another folder

When coscribe needs a folder outside the workspace and the folders you allowed, it asks on a card. Choose the access (**Read only**, **Read and write**, or **Read, write and delete**), then:

- **Allow** adds the folder to your allowed folders for good.
- **Only this chat** allows it for this conversation only.
- **Save in my workspace instead** (when it wanted to write) keeps the file in the workspace.
- **Don't allow** refuses.

coscribe never offers a whole drive or your home folder.

## Install a package for a script

A script may need a Python or Node.js library coscribe doesn't have yet. The card **Install a Python package** (or Node.js) names it and says why. **Install** installs it into coscribe's own environment, which the rest of your computer doesn't use; **Not now** says no for this conversation. If the install fails, **Details** shows the installer's output.

## Answer a question

Sometimes coscribe asks you to choose, for example between two layouts. Pick an option on the card, or type your own answer in the message box.
