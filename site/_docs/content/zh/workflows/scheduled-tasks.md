---
title: 定时任务
description: 让 coscribe 按时间表完成工作，比如每天早上的简报，并查看每次运行的报告。
---

定时任务是 coscribe 不需要你在场就能完成的工作：在设定的时间、每小时一次，或者在你启动它的时候。每次运行都是一个单独的对话，并以一份报告结束。

任务有两种。**定时任务**按照写好的指令执行，每一步都由模型现场决定。**工作流**执行你保存好的固定步骤，并在运行中逐步检查，见[工作流](workflows.md)。本页讲的是两者共有的部分。

## 创建任务 {#create-a-task}

在导航里打开 **Scheduled**，点 **New task**：

- **Create with Coscribe** 开一个对话，让你描述这项工作，或者带它做一遍。然后 coscribe 会在一张卡片里起草任务；**Review & save** 打开草稿，保存之前什么都可以改。
- **Set up manually** 打开表单，名称、指令和时间表都由你自己填写。
- **Build a workflow** 新建一个空的工作流，见[工作流](workflows.md)。

在对话里做完一项工作后，coscribe 也可能提示 **Save this job?**。**Save as workflow** 把它变成可以重跑或定时运行的固定步骤；**Save as skill** 把它存成下次照着做的说明（见[技能和插件](../customize/skills.md)）。

## 选择什么时候运行 {#choose-when-it-runs}

**Frequency** 可以是 **Manual**（只在你启动时运行）、**Hourly**、**Daily**、**Weekdays**、**Weekly** 或 **Monthly**。每天、工作日和每周运行需要设定时间，每周运行还要选星期几。工作流还可以每隔几分钟运行一次，或者在某件事发生时运行，见[在事件发生时启动工作流](workflows.md#start-on-an-event)。

任务还有一个 **Workspace**，决定它运行时能用哪些文件夹和网站（见[工作区](../workspaces/workspaces.md)），以及一个 **Model**。**Default model** 使用设置里的默认模型。

## 选择它不问你就能做什么 {#choose-what-it-may-do-without-you}

运行时没人看着，所以每个任务有自己的 **Permissions**：

| 设置 | 会怎样 |
|---|---|
| **Ask before every action** | 遇到需要批准的操作，运行会暂停，等你批准。 |
| **Automatically approve** | 自己新建和修改文件，但在运行代码或使用连接器之前暂停。 |
| **Never ask** | 从不暂停等待批准，包括运行代码和使用连接器。你的拦截规则仍然有效。 |

**Most steps** 规定运行到多少步就结束，这样出错的运行不会一直跑下去。

> [!WARNING]
> 选 **Never ask** 时，运行可以不经询问就运行代码、使用你的连接器。只对你信得过其指令的任务使用它。

## 让应用保持运行 {#keep-the-app-running}

关掉 coscribe 的窗口后，它会留在系统托盘里继续运行，任务照常执行。要退出，在托盘图标的菜单里选 **Quit**。如果在 **Settings** › **General** 里关掉 **Keep running in the background**，关窗口就会退出 coscribe，任务也随之停止。

coscribe 关闭期间到点的运行，会在 coscribe 再次启动时补跑一次。

## 跟进运行情况 {#follow-the-runs}

任务页面显示下次运行的时间、最近的运行及其状态：**Running**、**Completed**、**Failed**、**Needs approval**、**Waiting** 或 **Stopped**。打开一次运行可以看到它的对话和报告。需要批准的运行会在那里等你。

- **Run now** 立即运行一次，用来试试任务。
- 状态旁边的开关可以暂停或恢复任务。
- 铅笔图标用来改名或修改运行时间。

**Settings** › **General** 里的 **Notifications** 决定 coscribe 是每次运行结束都通知你，还是只在出问题时通知：运行失败或在等你。点击通知会打开那次运行。

## 让运行之间记住东西 {#remember-between-runs}

在定时任务的页面上打开 **Remember between runs**，每次运行都会给下一次留笔记：进度、停在哪里、有什么变化。关掉时，每次运行都从零开始。
