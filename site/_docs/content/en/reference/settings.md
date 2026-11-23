---
title: Settings
description: Every page of coscribe's settings and what each setting does.
---

Open settings with the gear at the top right, or <kbd>Ctrl</kbd> + <kbd>,</kbd> in the desktop app. The search box at the top finds a setting by name.

## General

| Setting | What it does |
|---|---|
| **Theme** | Light, dark, or the same as Windows. |
| **Interface font** | The font for menus, panels and conversations: Figtree, the system's own font, or OpenDyslexic. |
| **Motion** | **Reduced** cuts animation in streaming replies and elsewhere. |
| **Conversation view** | **Simple** shows each reply without the steps behind it, and one line saying what coscribe is doing. **Detailed** shows every step. |
| **What should Coscribe call you?** | The name in the greeting on the home screen. |
| **Default model** | The model a new conversation starts with. Each conversation can switch from its own model picker. |
| **Default mode** | The [permission mode](../get-started/first-conversation.md#permission-modes) a new conversation starts in. |
| **Global instructions** | What coscribe should always know. See [Instructions](../customize/instructions.md). |
| **Prompt suggestions** | After a reply, suggests your next message in the message box: <kbd>Enter</kbd> sends it, <kbd>Tab</kbd> puts it in the box to edit. Adds a little to your usage. |
| **Background agents** | Lets coscribe hand work to helpers that run in the background while you keep chatting. They can use a lot of your usage. |
| **Archive inactive conversations** | Archives conversations after 7, 30 or 90 days without activity, or never. A conversation that is open or has work running is never archived. |
| **Keep running in the background** | Closing the window keeps coscribe in the tray, so scheduled tasks still run. Off, closing the window quits. |
| **Notifications** | **All** task runs, **Problems only** (a run failed or is waiting for you), or **Off**. |
| **Draw attention when Coscribe needs you** | Flashes the taskbar button when a reply finishes or coscribe waits for you, and the window isn't in front. |
| **Keep computer awake while Coscribe works** | Stops the PC from sleeping during a reply, so long tasks can finish. The display can still turn off, and closing the lid still sleeps it. **Keep awake on battery power** does the same on battery. |
| **Proxy** | How coscribe reaches the internet: **System**, **Manual** (address, hosts to reach directly, user name and password) or **No proxy**. |

## Workspaces

The list of your [workspaces](../workspaces/workspaces.md): **New** adds one, and each one's **⋯** menu edits or deletes it. **Allowed folders** is the one list of folders outside a workspace's main folder, each with its access; a workspace reaches only the ones it picks. See [Allowed folders](../workspaces/workspaces.md#allowed-folders).

## Providers

The model services you connected and the models switched on for each. See [Connect a model](../get-started/providers.md).

## Capabilities

| Setting | What it does |
|---|---|
| **Create and edit files** | Lets coscribe write and change files in its workspace's folders. Off, it only reads them and answers in the conversation. |
| **Artifacts** | Docs, designs and dashboards that open beside the conversation. See [Artifacts](../office/artifacts.md). |
| **Run scripts** | For work too big for the built-in tools, coscribe writes a Python or Node.js script and runs it after you approve it, kept to the workspace's folders. See [Scripts and isolation](../workspaces/workspaces.md#scripts-and-isolation). |
| **Run commands** | Command lines in cmd or PowerShell, for what a script can't do, such as git or an installer. You approve each one. **Command sandbox** and **Private folders** set what a command can reach. |
| **Chats can hand tasks to Code** | Lets a conversation give a coding job to Codex, a coding agent. **Model for code** picks its model; **Change files without asking** lets it edit without asking for each change. |
| **Python for scripts**, **Packages for scripts** | Which Python runs scripts, and extra Python and Node.js libraries they may use. |
| **LibreOffice**, **Codex** | Optional downloads, which you install, update or remove here. LibreOffice makes page previews. |

## Secrets {#secrets}

Keys and tokens you add once, then give to the workspaces that need them. coscribe can use a secret in a web request only for the hosts you allow, and the model never sees its value: it is kept out of messages, tool results and logs. Secrets are kept in Windows Credential Manager, never in a plain file.

> [!IMPORTANT]
> This keeps the value out of what the model reads. It is not a defence against a program that goes looking: anything coscribe runs on your PC runs as you and could read the keychain itself.

## Skills, Connectors, Design systems

See [Skills and plugins](../customize/skills.md), [Connectors](../customize/connectors.md) and [Design systems](../customize/design-systems.md).
