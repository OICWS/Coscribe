---
title: Privacy and safety
description: What leaves your computer when you use Coscribe, where your data is kept, and what keeps its actions in check.
---

Coscribe runs on your PC. It has no account and no server of its own, and it sends nothing about you or your use to its makers.

## What leaves your computer

| Goes to | What | When |
|---|---|---|
| The model provider you picked | Your messages, the parts of files Coscribe reads to answer, and the results of its tools | Every reply. A [model on your PC](../get-started/providers.md#run-a-model-on-your-pc) keeps this on your computer too. |
| Search engines | The search words | When Coscribe searches the web. It uses free engines such as DuckDuckGo, with no key. |
| Websites | Ordinary page requests | When Coscribe opens a page you asked for, or that a task needs. See [The built-in browser](../use/browser.md). |
| Services you connected | What a connector's tool sends | When Coscribe uses that [connector](../customize/connectors.md). |

The provider's own terms decide what it keeps and for how long. Read them before you send it work documents.

## Where your data is kept

Everything else stays on your PC:

- Your files stay where they are; Coscribe works on them in place.
- Conversations, scheduled tasks, skills and settings are under `%APPDATA%\Coscribe`.
- API keys and [secrets](../reference/settings.md#secrets) are in Windows Credential Manager, never in a plain file.
- A record of how each turn went (the model, tool calls, errors, tokens and time, without the conversation's words) stays on your PC for troubleshooting. Nothing uploads it.

## What keeps actions in check

- **Folders**: Coscribe writes only to its workspace and the other folders you allowed. See [Workspaces](../workspaces/workspaces.md).
- **Approvals**: actions that change things wait for you, as the [permission mode](../use/approvals.md) says. A file Coscribe deletes with its own file tools goes to the Recycle Bin.
- **Scripts** run in an isolated container where Windows allows it, kept to the workspace's folders; where isolation can't be set up, scripts are off unless you choose otherwise. See [Scripts and isolation](../workspaces/workspaces.md#scripts-and-isolation).
- **Sites**: what Coscribe may open in the browser follows the workspace's sites setting. See [Allow a site](../use/browser.md#allow-a-site).

> [!IMPORTANT]
> Approvals are a check by you, not a sandbox. A script or command you approve can do what your Windows account can do, unless isolation holds it. Read what an approval card says before you click **Allow**.

## Things to watch for

- Text from the web, an email or a document can contain instructions meant for an AI. Coscribe treats what it reads as material, not as orders from you, but no model is perfect: be careful with **Never ask** and **Auto** when a task reads things others wrote.
- Add skills, plugins and connectors only from people you trust.
