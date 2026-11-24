---
title: 文件夹自己的说明和规则
description: 让文件夹告诉 Coscribe 它装着什么、用哪些技能和连接器，以及哪些操作不用问。
---

文件夹可以在里面的 `.coscribe` 文件夹里给 Coscribe 留下说明。任何使用这个文件夹的对话都会读取它们，前提是你已经接受。

## 文件夹里可以放什么 {#what-a-folder-can-hold}

| 文件 | 作用 |
|---|---|
| `.coscribe/memory.md` | Coscribe 在这个文件夹里每次开始对话时读的笔记：文件夹的用途、惯例、名称。 |
| `.coscribe/skills/<name>/SKILL.md` | 只在这个文件夹里生效的[技能](../customize/skills.md)。 |
| `.coscribe/settings.json` | 权限规则（`allow`、`ask`、`deny`）和脚本的环境变量。 |
| `.coscribe/mcp.json` | 这个文件夹使用的[连接器](../customize/connectors.md)。 |

Coscribe 自己从不写 `memory.md`、`settings.json` 或 `mcp.json`，只有你会编辑它们。你发送的附件保存在 `.coscribe/uploads/` 里。

## 接受文件夹的设置 {#accept-a-folders-settings}

文件夹里的设置可能来自任何能写这个文件夹的人，所以在你同意之前 Coscribe 不会照做。**Task details** 面板会显示 **What Coscribe knows about this folder**，列出文件夹带来的技能、连接器和规则，分为 **Runs without asking**、**Always asks** 和 **Never runs**，以及给脚本的变量。点 **Use them** 接受。

只要这些文件在 Coscribe 之外被改动，它就会再问一次。

## 权限规则 {#permission-rules}

`.coscribe/settings.json` 的格式和 Claude Code 的设置文件相同：

```json
{
  "permissions": {
    "allow": ["write_file(reports/*)"],
    "ask": ["run_background_command"],
    "deny": ["delete_file"]
  },
  "env": {
    "REPORT_REGION": "East"
  }
}
```

一条规则是一个 Coscribe 工具名、一个用 `*` 匹配名称的模式，或者在它们后面用括号加上主参数的模式，比如 `write_file(docs/*)`。规则只决定那些本来要等你批准的操作。**deny** 优先于 **ask**，**ask** 优先于 **allow**。

有几条限制始终有效：

- 规则永远不会放行离开你电脑的操作，比如通过连接器发消息；这类操作仍然会问。
- 单独一个 `*` 不放行任何操作。
- `ask` 规则在 **Auto** 模式下也会询问。

## 脚本的变量 {#variables-for-scripts}

`settings.json` 里的 `env` 值会传给这个文件夹里的脚本和命令。文件夹不能设置会改变运行哪个程序或流量去向的变量，比如 `PATH`、代理设置或 `PYTHONPATH`。
