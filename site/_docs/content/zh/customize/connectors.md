---
title: 连接器
description: 把 coscribe 接到你常用的服务上，比如邮箱、日历或项目管理工具，并决定它在那里能做什么。
---

连接器让 coscribe 能使用另一个服务：读你的邮件、在日历里加一个日程、查一个工单。连接器使用模型上下文协议（MCP），所以任何 MCP 服务器都能用，不限于 coscribe 列出的那些。

## 添加连接器 {#add-a-connector}

打开 **Settings** › **Connectors** › **Discover**，选择服务，点 **Connect**。

- 大多数在线服务需要你登录。登录页面是服务自己的，在你的浏览器里打开，只需登录一次。coscribe 看不到你的密码。
- 标着 **Needs setup** 的服务需要先在它那里注册一个应用。coscribe 会一步步带你完成，只需做一次。如果团队里已经有人设置好了，**Copy a message for your admin** 可以向他们要设置文件。

当你的请求需要一个还没连接的服务时，coscribe 也会在对话里推荐连接器。点卡片上的 **Connect**，连接好后 coscribe 会接着做。**Not now** 表示先不连；之后随时可以在 **Settings** › **Connectors** 里连接。

## 添加自定义连接器 {#add-a-custom-connector}

对于没有列出的 MCP 服务器，选择 **Add** › **Add custom connector**，起个名字，然后二选一：

- 填写在线服务器的 **MCP server URL**，以及它需要的请求头。要在请求头里放密钥又不想明文写出来，用 **Insert a secret**；请求头里会写成 `{{secret:NAME}}`，值来自[密钥](../reference/settings.md#secrets)。
- 或者选 **Run a local command instead**，填写命令（比如 `npx`）、参数和环境变量。它会作为本机上的一个程序运行，拥有你的权限。

> [!WARNING]
> 本地命令能做你的 Windows 账户能做的一切。只添加你信任的服务器。

## 决定它能做什么 {#choose-what-it-may-do}

在 **Yours** 里打开一个连接器，可以看到它的工具，分为 **Read-only tools** 和 **Write/delete tools**。为每个工具选择：

| 选项 | 会怎样 |
|---|---|
| **Always allow** | coscribe 直接使用，不问你。 |
| **Needs approval** | 每次都问你。见[审批](../use/approvals.md)。 |
| **Blocked** | coscribe 不能使用。 |

连接器的页面还会显示它是否已连接。没有连接时，**Retry** 重新连接，**Sign in** 打开服务的登录页面。

## 只在一个文件夹里用的连接器 {#connectors-for-one-folder}

文件夹可以在 `.coscribe/mcp.json` 里带上自己的连接器。你接受这个文件夹的设置后，它们只在使用这个文件夹的对话里生效。见[文件夹自己的说明和规则](../workspaces/folder-settings.md)。

## 在工作流里使用连接器 {#use-a-connector-in-a-workflow}

连接器的工具可以作为[工作流](../workflows/workflows.md)的步骤，工作流也可以在连接器里出现新内容时启动。见[在事件发生时启动工作流](../workflows/workflows.md#start-on-an-event)。
