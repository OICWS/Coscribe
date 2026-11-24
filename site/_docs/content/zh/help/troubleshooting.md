---
title: 排查问题
description: 用 /doctor 检查 Coscribe 在电脑上需要的东西，解决常见问题，并报告问题。
---

## 运行检查 {#run-a-check}

在任意对话里输入 `/doctor`。Coscribe 会检查它在这台电脑上需要的东西，并显示一张卡片，列出每项结果（问题排在最前）和对应的解决办法。如果解决办法是某个设置，会直接链接到那一页。

| 检查项 | 检查什么 |
|---|---|
| **Model** | 默认模型能否回答。不能的话：检查服务商的密钥、地址和模型名称，或者网络和[代理](../reference/settings.md#general)。 |
| **Python for scripts** | 有没有可以运行脚本的 Python。没有的话，在 **Settings** › **Capabilities** 里下载 Coscribe 自带的 Python。 |
| **Node.js for scripts** | 有没有安装 `node` 和 `npm`，用于 Node.js 脚本。需要的话从 [nodejs.org](https://nodejs.org) 安装。 |
| **Office conversion** | 有没有 Microsoft Office 或 LibreOffice 用来生成页面预览和转换文档。都没有的话，安装 Office，或在 **Settings** › **Capabilities** 里下载 LibreOffice。 |
| **Browser** | 有没有安装 Microsoft Edge 或 Google Chrome，用于浏览器面板和网页截图。 |
| **Script isolation** | 脚本能否在隔离容器里运行。自检通过之前脚本是关闭的；可以在工作区设置里重新运行自检。 |
| **Command sandbox** | 命令是否在沙箱里运行。没有设置时，每条命令都以你的身份运行，并且要你批准。 |

## 常见问题 {#common-problems}

### 回答失败或一直没有回答 {#a-reply-fails-or-never-comes}

运行 `/doctor`，看 **Model** 一项。常见原因是密钥过期、模型名称写错，或者网络需要代理。有些公司网络会屏蔽 AI 服务，可以问问 IT 部门，或者在 **Settings** › **General** › **Proxy** 里设置代理。

### Coscribe 打不开某个文件或文件夹 {#coscribe-cant-open-a-file-or-folder}

Coscribe 只在它的工作区和你允许的文件夹里工作。它请求访问另一个文件夹时，允许它，或者把这个文件夹加进工作区。见[允许访问另一个文件夹](../use/approvals.md#give-access-to-another-folder)。

如果你也在编辑同一个 Word、Excel 或 PowerPoint 文件，提要求前先保存。Coscribe 会发现文件在它上次读取后变了，重新读取并在你的版本上修改，但它只能看到你保存过的内容。

### 脚本不运行 {#scripts-dont-run}

确认 **Settings** › **Capabilities** 里的 **Run scripts** 是打开的，然后运行 `/doctor`，看 **Python for scripts** 和 **Script isolation**。

### 连接器不能用了 {#a-connector-stops-working}

在 **Settings** › **Connectors** 里打开它。如果显示未连接，点 **Retry**；登录过期的话点 **Sign in**。

### 定时任务没有运行 {#a-scheduled-task-didnt-run}

任务只在 Coscribe 运行时执行，无论是在窗口里还是在托盘里。确认 **Settings** › **General** 里的 **Keep running in the background** 是打开的，并且任务没有被暂停。Coscribe 关闭期间到点的运行，会在它再次启动时补跑一次。见[定时任务](../workflows/scheduled-tasks.md)。

## 报告问题 {#report-a-problem}

到 [GitHub](https://github.com/OICWS/coscribe/issues/new) 上报告。写清楚你要它做什么、实际发生了什么，以及 `/doctor` 显示了什么。

想说明某一轮哪里出了错、又不想分享对话内容，可以在侧边栏右键点击对话，选择 **Export a failed turn…**。这个文件记录了那一轮是怎么进行的：模型、工具调用和失败、用量和耗时，以及每个工具错误的开头。它不含对话里的任何文字，也不会自动发送：文件由你保存，由你决定给谁。

服务器日志在 `%APPDATA%\Coscribe\logs\coscribe-server.log`。
