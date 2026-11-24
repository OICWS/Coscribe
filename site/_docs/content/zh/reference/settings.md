---
title: 设置
description: Coscribe 设置里的每一页，以及每个设置的作用。
---

点右上角的齿轮打开设置，在桌面应用里也可以按 <kbd>Ctrl</kbd> + <kbd>,</kbd>。顶部的搜索框可以按名称找到某个设置。

## General {#general}

| 设置 | 作用 |
|---|---|
| **Theme** | 浅色、深色，或跟随 Windows。 |
| **Interface font** | 菜单、面板和对话用的字体：Figtree、系统字体或 OpenDyslexic。 |
| **Motion** | **Reduced** 减少回答流式输出和其他地方的动画。 |
| **Conversation view** | **Simple** 只显示回答，不显示背后的步骤，加一行说明 Coscribe 正在做什么。**Detailed** 显示每一步。 |
| **What should Coscribe call you?** | 首页问候语里用的名字。 |
| **Default model** | 新对话使用的模型。每个对话都可以用自己的模型选择器切换。 |
| **Default mode** | 新对话开始时的[权限模式](../get-started/first-conversation.md#permission-modes)。 |
| **Global instructions** | Coscribe 应该一直知道的事。见[指令](../customize/instructions.md)。 |
| **Prompt suggestions** | 回答之后在输入框里建议你的下一条消息：<kbd>Enter</kbd> 直接发送，<kbd>Tab</kbd> 放进输入框编辑。会增加一点用量。 |
| **Background agents** | 允许 Coscribe 把工作交给在后台运行的助手，你可以继续聊天。它们可能用掉很多用量。 |
| **Archive inactive conversations** | 对话 7、30 或 90 天没有动静后归档，或者从不归档。打开着或有工作在运行的对话永远不会被归档。 |
| **Keep running in the background** | 关掉窗口后 Coscribe 留在系统托盘里，定时任务照常运行。关掉这个选项，关窗口就会退出。 |
| **Notifications** | **All**：每次任务运行都通知；**Problems only**：只在运行失败或等你时通知；**Off**：不通知。 |
| **Draw attention when Coscribe needs you** | 回答完成或 Coscribe 在等你、而窗口不在前台时，让任务栏按钮闪烁。 |
| **Keep computer awake while Coscribe works** | 回答进行中不让电脑睡眠，好让长任务做完。显示器仍可关闭，合上笔记本盖子仍会睡眠。**Keep awake on battery power** 让它在用电池时也这样做。 |
| **Proxy** | Coscribe 怎样连接互联网：**System**、**Manual**（地址、直连的主机、用户名和密码）或 **No proxy**。 |

## Workspaces {#workspaces}

你的[工作区](../workspaces/workspaces.md)列表：**New** 新建，每个工作区的 **⋯** 菜单可以编辑或删除它。**Allowed folders** 是工作区主文件夹之外所有文件夹的统一列表，各有自己的权限；工作区只能碰到它选中的那些。见[已允许的文件夹](../workspaces/workspaces.md#allowed-folders)。

## Providers {#providers}

你接入的模型服务，以及每个服务打开了哪些模型。见[添加模型服务商](../get-started/providers.md)。

## Capabilities {#capabilities}

| 设置 | 作用 |
|---|---|
| **Create and edit files** | 允许 Coscribe 在工作区的文件夹里写和改文件。关掉后它只读文件，在对话里回答。 |
| **Artifacts** | 在对话旁边打开的文档、设计和仪表板。见[文档、设计和仪表板](../office/artifacts.md)。 |
| **Run scripts** | 内置工具做不了的大活，Coscribe 会写 Python 或 Node.js 脚本，经你批准后运行，范围限于工作区的文件夹。见[脚本和隔离](../workspaces/workspaces.md#scripts-and-isolation)。 |
| **Run commands** | cmd 或 PowerShell 的命令行，用来做脚本做不了的事，比如 git 或安装程序。每条都要你批准。**Command sandbox** 和 **Private folders** 决定命令能碰到什么。 |
| **Chats can hand tasks to Code** | 允许对话把编程工作交给编程智能体 Codex。**Model for code** 选择它用的模型；**Change files without asking** 让它修改文件时不再逐个询问。 |
| **Python for scripts**、**Packages for scripts** | 用哪个 Python 运行脚本，以及脚本能用的额外 Python 和 Node.js 库。 |
| **LibreOffice**、**Codex** | 可选的下载，在这里安装、更新或删除。LibreOffice 用来生成页面预览。 |

## Secrets {#secrets}

密钥和令牌只需添加一次，再交给需要它们的工作区。Coscribe 只能在你允许的主机的网络请求里使用密钥，模型永远看不到它的值：消息、工具结果和日志里都不会出现。密钥保存在 Windows 凭据管理器里，从不写进普通文件。

> [!IMPORTANT]
> 这能让模型读不到密钥的值，但挡不住有意去找的程序：Coscribe 在你电脑上运行的任何东西都以你的身份运行，它自己就能读取凭据管理器。

## Skills、Connectors、Design systems {#skills-connectors-design-systems}

见[技能和插件](../customize/skills.md)、[连接器](../customize/connectors.md)和[设计系统](../customize/design-systems.md)。
