---
title: 隐私和安全
description: 使用 Coscribe 时哪些内容会离开你的电脑，数据存在哪里，以及有什么在约束它的操作。
---

Coscribe 运行在你的电脑上。它没有账号，没有自己的服务器，也不会把关于你或你使用情况的任何信息发给它的开发者。

## 什么会离开你的电脑 {#what-leaves-your-computer}

| 发往 | 内容 | 什么时候 |
|---|---|---|
| 你选择的模型服务商 | 你的消息、Coscribe 为了回答而读取的文件内容，以及它的工具结果 | 每次回答。用[本机上的模型](../get-started/providers.md#run-a-model-on-your-pc)，这些也留在你的电脑上。 |
| 搜索引擎 | 搜索关键词 | Coscribe 搜索网络时。它使用 DuckDuckGo 等免费搜索引擎，不需要密钥。 |
| 网站 | 普通的网页请求 | Coscribe 打开你要的网页，或任务需要的网页时。见[内置浏览器](../use/browser.md)。 |
| 你连接的服务 | 连接器的工具发送的内容 | Coscribe 使用那个[连接器](../customize/connectors.md)时。 |

服务商会保留什么、保留多久，由它自己的条款决定。把工作文档发给它之前，请先读一读。

## 数据存在哪里 {#where-your-data-is-kept}

其余的一切都留在你的电脑上：

- 你的文件待在原处，Coscribe 直接在原位置处理它们。
- 对话、定时任务、技能和设置都在 `%APPDATA%\Coscribe` 下。
- API 密钥和[密钥](../reference/settings.md#secrets)保存在 Windows 凭据管理器里，从不写进普通文件。
- 每一轮的运行记录（模型、工具调用、错误、用量和耗时，不含对话内容）保存在你的电脑上，用于排查问题。不会上传到任何地方。

## 什么在约束它的操作 {#what-keeps-actions-in-check}

- **文件夹**：Coscribe 只写入它的工作区和你允许的其他文件夹。见[工作区](../workspaces/workspaces.md)。
- **审批**：会改变东西的操作，要按[权限模式](../use/approvals.md)的规定等你同意。Coscribe 用自己的文件工具删除的文件会进回收站。
- **脚本**：在 Windows 允许的地方，脚本在隔离容器里运行，范围限于工作区的文件夹；无法建立隔离时，脚本默认关闭，除非你另做选择。见[脚本和隔离](../workspaces/workspaces.md#scripts-and-isolation)。
- **网站**：Coscribe 能在浏览器里打开哪些网站，由工作区的网站设置决定。见[允许一个网站](../use/browser.md#allow-a-site)。

> [!IMPORTANT]
> 审批是由你把关，而不是沙箱。你批准的脚本或命令能做你的 Windows 账户能做的事，除非有隔离限制它。点 **Allow** 之前，请读一下审批卡片上写了什么。

## 需要留意的地方 {#things-to-watch-for}

- 网页、邮件或文档里的文字，可能藏着写给 AI 的指令。Coscribe 把读到的内容当作材料，而不是你的命令，但没有模型是完美的：任务要读别人写的东西时，慎用 **Never ask** 和 **Auto**。
- 技能、插件和连接器只从你信任的人那里添加。
