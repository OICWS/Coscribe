---
title: 命令和快捷键
description: 可以在输入框里输入的命令，以及 Coscribe 的键盘快捷键。
---

## 命令 {#commands}

在输入框里输入 <kbd>/</kbd> 会列出命令；继续输入可以筛选，<kbd>Enter</kbd> 执行高亮的那一个。

| 命令 | 作用 |
|---|---|
| `/compact` | 总结对话，腾出上下文空间。见[模型、思考强度和上下文](../use/models.md#watch-the-context)。 |
| `/clear` | 归档这个对话，在同一个工作区开一个新对话。 |
| `/fork [名字]` | 把对话复制成一个新对话并打开。见[复制一个对话](../use/conversations.md#copy-a-conversation)。 |
| `/init` | 浏览工作区，在根目录写入或更新 `OVERVIEW.md`。 |
| `/create-skill <名字>` | 把这个对话变成可以重复使用的技能。见[技能和插件](../customize/skills.md)。 |
| `/doctor` | 检查 Coscribe 在这台电脑上需要的东西。见[排查问题](../help/troubleshooting.md)。 |
| `/<技能>` | 用这个技能处理你的请求。你的每个技能都以自己的名字出现在列表里。 |

有几个命令不在列表里，因为有按钮能做同样的事，但直接输入也能用：

| 命令 | 作用 |
|---|---|
| `/plan` | 打开 **Plan** 模式；已经打开时回到 **Manual**。 |
| `/accept-edits` | 打开 **Accept Edits** 模式，或回到 **Manual**。 |
| `/auto` | 打开 **Auto** 模式，或回到 **Manual**。 |
| `/stop` | 停下正在进行的回答。 |
| `/saveworkflow [名字]` | 根据对话起草一个工作流。见[工作流](../workflows/workflows.md)。 |

## 键盘快捷键 {#keyboard-shortcuts}

在文本框之外的任何地方按 <kbd>?</kbd>，或者点右上角的键盘图标，就能在应用里看到快捷键。

### 任何地方 {#everywhere}

| 按键 | 作用 |
|---|---|
| <kbd>?</kbd> | 显示快捷键列表。 |
| <kbd>Esc</kbd> | 关闭对话框，或取消编辑消息。 |

### 输入框里 {#in-the-message-box}

| 按键 | 作用 |
|---|---|
| <kbd>Enter</kbd> | 发送消息。 |
| <kbd>Shift</kbd> + <kbd>Enter</kbd> 或 <kbd>Ctrl</kbd> + <kbd>Enter</kbd> | 换行。 |
| <kbd>/</kbd> | 打开命令列表。 |

### 模型选择器里 {#in-the-model-picker}

| 按键 | 作用 |
|---|---|
| <kbd>1</kbd> 到 <kbd>9</kbd> | 切换到对应编号的模型。 |

### 桌面应用里 {#in-the-desktop-app}

| 按键 | 作用 |
|---|---|
| <kbd>Ctrl</kbd> + <kbd>N</kbd> | 新对话。 |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>O</kbd> | 选择工作区。 |
| <kbd>Ctrl</kbd> + <kbd>,</kbd> | 打开设置。 |
| <kbd>Ctrl</kbd> + <kbd>W</kbd> | 离开这个对话，开一个新对话。 |
| <kbd>Ctrl</kbd> + <kbd>F</kbd> | 在页面中查找；<kbd>F3</kbd> 和 <kbd>Shift</kbd> + <kbd>F3</kbd> 跳到下一个和上一个结果。 |
| <kbd>Alt</kbd> + <kbd>←</kbd> / <kbd>Alt</kbd> + <kbd>→</kbd> | 回到上一页，或再前进。 |
| <kbd>Ctrl</kbd> + <kbd>/</kbd> | 显示快捷键列表。 |
