---
title: Troubleshooting
description: Check what Coscribe needs on your PC with /doctor, fix common problems, and report one.
---

## Run a check

Type `/doctor` in any conversation. Coscribe checks what it needs on this computer and shows a card with each result, problems first, and how to fix each one. A fix that is a setting links to its page.

| Check | What it looks at |
|---|---|
| **Model** | Whether the default model answers. If not: check the provider's key, address and model name, or the network and [proxy](../reference/settings.md#general). |
| **Python for scripts** | Whether a Python is there for scripts. If not, download Coscribe's own under **Settings** › **Capabilities**. |
| **Node.js for scripts** | Whether `node` and `npm` are installed, for scripts in Node.js. Install them from [nodejs.org](https://nodejs.org) if you need them. |
| **Office conversion** | Whether Microsoft Office or LibreOffice is there to make page previews and convert documents. If neither is, install Office or download LibreOffice under **Settings** › **Capabilities**. |
| **Browser** | Whether Microsoft Edge or Google Chrome is installed, for the browser panel and page pictures. |
| **Script isolation** | Whether scripts can run in their isolated container. Until the self-test passes, scripts are off; run it again in the workspace's settings. |
| **Command sandbox** | Whether commands run in the sandbox. If it isn't set up, each command runs as you, after you approve it. |

## Common problems

### A reply fails or never comes

Run `/doctor` and look at **Model**. A key that expired, a wrong model name, or a network that needs a proxy are the usual causes. Some company networks block AI services; ask your IT team, or set the proxy in **Settings** › **General** › **Proxy**.

### Coscribe can't open a file or folder

Coscribe only works in its workspace and the folders you allowed. When it asks for another folder, allow it, or add the folder to the workspace. See [Give access to another folder](../use/approvals.md#give-access-to-another-folder).

If you're editing the same Word, Excel or PowerPoint file, save your changes before you ask. Coscribe notices when a file changed since it last read it, reads it again and makes its change on your version, but it can only see what you saved.

### Scripts don't run

Make sure **Run scripts** is on in **Settings** › **Capabilities**, then run `/doctor` and look at **Python for scripts** and **Script isolation**.

### A connector stops working

Open it in **Settings** › **Connectors**. If it says it isn't connected, click **Retry**, or **Sign in** when its sign-in ran out.

### A scheduled task didn't run

Tasks run only while Coscribe is running, in the window or the tray. Check that **Keep running in the background** is on in **Settings** › **General** and that the task isn't paused. A run that was due while Coscribe was closed runs once when it starts again. See [Scheduled tasks](../workflows/scheduled-tasks.md).

## Report a problem

Report it on [GitHub](https://github.com/OICWS/coscribe/issues/new). Say what you asked for, what happened instead, and what `/doctor` shows.

To show how a turn went wrong without sharing your words, right-click the conversation in the sidebar and choose **Export a failed turn…**. The file says how the turn went: the model, its tool calls and failures, tokens and time, and the start of each tool error. It holds none of the conversation's words, and nothing is sent: you save the file and decide who gets it.

The server's log is `%APPDATA%\Coscribe\logs\coscribe-server.log`.
