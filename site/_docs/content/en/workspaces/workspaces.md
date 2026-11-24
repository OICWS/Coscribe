---
title: Workspaces and folders
description: Decide which folders, sites, secrets and scripts each conversation can reach.
---

A **workspace** is the folder a conversation works in, together with what it may reach beyond it: other folders, websites, secrets and scripts. Each conversation uses one workspace. Conversations that don't pick one use the **Default** workspace.

## Pick a workspace for a conversation

Use the workspace picker below the message box. It lists your workspaces and offers **New workspace**. The **Default** workspace is used by every conversation that hasn't chosen another.

## Edit a workspace

Open **Settings › Workspaces** and choose **Edit** from a workspace's **⋯** menu, or create one with **New**. The dialog has a name, the main **Folder** (new files, screenshots and artifacts go here) and one row per kind of reach. Each row shows what is set and opens its own page:

| Page | What it sets |
|---|---|
| **Allowed folders** | Other folders this workspace may use, each with its access. Other workspaces don't reach them. |
| **Sites** | Which websites it may use: **None**, **Listed sites** or **Any site**, and how the [built-in browser](../use/browser.md#allow-a-site) treats each listed site. |
| **Secrets** | Which of your saved secrets it may send in a web request. The model never sees a secret's value. |
| **Scripts and commands** | Whether it may run Python and Node.js **Scripts**, and **Commands**. |
| **Environment variables** | Values passed to its scripts and commands. |

What the **Sites** choice means:

- **None**: no web search, web pages, downloads or browser steps, and scripts stay offline.
- **Listed sites**: it opens, downloads from and uses in the browser only the listed sites and their subdomains. Search still works; scripts stay offline.
- **Any site**: any site. List a site to choose how the browser uses it.

## Allowed folders

Every folder Coscribe may use outside a workspace's main folder is kept in one list, **Allowed folders**, under **Settings › Workspaces › Manage**. Each folder there has an access level (**Read only**, **Read and write**, or **Read, write and delete**). A workspace reaches only the allowed folders it picks on its **Allowed folders** page: **Use an allowed folder** picks one from the list, and **Add new folder…** adds a new one, which joins the list as read and write.

Removing a folder from **Allowed folders** removes it from every workspace. A folder that can't be found right now, such as an unplugged drive, is marked and used again when it comes back.

When a conversation needs a folder it can't reach, it asks on a card; see [Give access to another folder](../use/approvals.md#give-access-to-another-folder).

## Scripts and isolation

On Windows, scripts run isolated: they can use only the conversation's folders, can't delete or rename files there, and reach the internet only when the workspace's **Sites** setting is **Any site**. Coscribe checks once whether isolation works on your computer. If the check failed, scripts are off; **Run scripts without isolation** on the **Scripts and commands** page turns them back on for that workspace, with the risk that comes with it.
