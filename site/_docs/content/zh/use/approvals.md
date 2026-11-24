---
title: 审批和权限模式
description: 决定 Coscribe 能自己做多少，以及在它需要你时怎么回答它的卡片。
---

没有你的同意，Coscribe 不会做超出范围的事。它多久问你一次取决于对话的权限模式；它到底能碰到什么，取决于[工作区](../workspaces/workspaces.md)。

## 四种模式 {#the-four-modes}

用输入框下方的模式按钮选择。新对话的默认模式在 **Settings › General › Default mode** 里设置。

| 模式 | 它会怎么做 |
|---|---|
| **Manual** | 每次修改、运行脚本或对外操作之前都问你。 |
| **Accept Edits** | 直接修改你文件夹里的文件；运行代码或对外操作之前仍然会问。 |
| **Plan** | 先调研，写出计划等你批准，之后才动手。见[计划和任务清单](plans.md)。 |
| **Auto** | 由一个审核模型批准常规操作、拦下有风险的操作，不再问你。 |

回答进行中切换模式，新模式在这次回答结束后生效。

## 批准一个操作 {#approve-an-action}

需要你批准时，对话里会出现一张卡片，写明操作（比如 “Run a command”）以及它要做什么：要写的文件、脚本或命令。看清楚后选择：

- **Approve** 允许这一次操作。
- **Allow for this task**（只在代码模块的命令和修改上出现）允许这个任务余下的部分里同类操作不再询问。
- **Deny** 拒绝。想说明原因，就在输入框里写下理由，Coscribe 会读到并调整。

如果卡片已经滚出视野，输入框上方会提示有东西在等你；点 **Show** 回到卡片。

> [!IMPORTANT]
> 脚本的卡片会说明它怎么运行。通常脚本在隔离中运行：只能用对话的文件夹，不能删除或重命名其中的文件，只有工作区的 **Sites** 设为 **Any site** 时才能上网。**Not isolated** 标记表示这个脚本会在没有隔离的情况下运行，能碰到你能碰到的任何文件；把鼠标移到标记上可以看原因，批准之前请读一下脚本。

## 允许访问另一个文件夹 {#give-access-to-another-folder}

Coscribe 需要工作区和已允许文件夹之外的文件夹时，会用卡片来问。选好权限（**Read only**、**Read and write** 或 **Read, write and delete**），然后：

- **Allow** 把这个文件夹永久加入已允许的文件夹。
- **Only this chat** 只在这个对话里允许。
- **Save in my workspace instead**（它要写文件时出现）把文件存在工作区里。
- **Don't allow** 拒绝。

Coscribe 从不会请求整个磁盘或你的用户主文件夹。

## 为脚本安装一个包 {#install-a-package-for-a-script}

脚本可能需要 Coscribe 还没有的 Python 或 Node.js 库。**Install a Python package**（或 Node.js）卡片会写明是哪个库、为什么需要。**Install** 把它装进 Coscribe 自己的环境，电脑上的其他程序不会用到；**Not now** 表示这个对话里不装。安装失败时，**Details** 会显示安装程序的输出。

## 回答一个问题 {#answer-a-question}

有时 Coscribe 会让你做选择，比如两种版式选哪个。在卡片上点一个选项，或者在输入框里写下你自己的答案。
