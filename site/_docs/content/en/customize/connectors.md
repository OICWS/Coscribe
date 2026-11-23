---
title: Connectors
description: Connect coscribe to the services you use, such as your mail, calendar or project tracker, and choose what it may do there.
---

A connector lets coscribe use another service: read your mail, add an event to a calendar, look up a ticket. Connectors use the Model Context Protocol (MCP), so any MCP server works, not only the ones coscribe lists.

## Add a connector

Open **Settings** › **Connectors** › **Discover**, pick the service and click **Connect**.

- Most hosted services ask you to sign in. The sign-in opens on the service's own page, in your browser, and you sign in only once. coscribe never sees your password.
- A service marked **Needs setup** wants an app registered with it first. coscribe walks you through it, one time only. If someone already set it up for your team, **Copy a message for your admin** asks them for the setup file.

coscribe can also offer a connector in a conversation, when your request needs a service you haven't connected. Click **Connect** on the card, and coscribe carries on once it's connected. **Not now** leaves it; you can connect it any time in **Settings** › **Connectors**.

## Add a custom connector

For an MCP server that isn't listed, choose **Add** › **Add custom connector**, give it a name, and either:

- Enter the **MCP server URL** of a hosted server, with any headers it needs. To put a key in a header without writing it out, use **Insert a secret**; the header then reads `{{secret:NAME}}` and the value comes from [Secrets](../reference/settings.md#secrets).
- Or choose **Run a local command instead** and enter the command, such as `npx`, its arguments and any environment variables. It runs as a program on this computer, with your permissions.

> [!WARNING]
> A local command runs with everything your Windows account can do. Add only servers you trust.

## Choose what it may do

Open a connector in **Yours** to see its tools, split into **Read-only tools** and **Write/delete tools**. For each tool, pick:

| Choice | What happens |
|---|---|
| **Always allow** | coscribe uses it without asking. |
| **Needs approval** | coscribe asks you each time. See [Approvals](../use/approvals.md). |
| **Blocked** | coscribe can't use it. |

The connector's page also says whether it's connected. If it isn't, **Retry** connects again, and **Sign in** opens the service's sign-in page.

## Connectors for one folder

A folder can bring its own connectors in `.coscribe/mcp.json`. They apply only in conversations that use that folder, once you've accepted its settings. See [A folder's own notes and rules](../workspaces/folder-settings.md).

## Use a connector in a workflow

A connector's tools can be steps of a [workflow](../workflows/workflows.md), and a workflow can start when something new shows up in a connector. See [Start a workflow on an event](../workflows/workflows.md#start-on-an-event).
