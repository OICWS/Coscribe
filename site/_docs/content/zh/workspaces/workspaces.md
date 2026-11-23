---
title: 工作区和文件夹
description: 决定每个对话能碰到哪些文件夹、网站、密钥和脚本。
---

**工作区**是对话工作的文件夹，加上它在这个文件夹之外还能碰到的东西：其他文件夹、网站、密钥和脚本。每个对话用一个工作区。没有选择的对话使用 **Default** 工作区。

## 为对话选择工作区 {#pick-a-workspace-for-a-conversation}

用输入框下方的工作区选择器。它列出你的工作区，并提供 **New workspace**。所有没有另选的对话都使用 **Default** 工作区。

## 编辑工作区 {#edit-a-workspace}

打开 **Settings › Workspaces**，在工作区的 **⋯** 菜单里选 **Edit**，或者用 **New** 新建一个。对话框里有名称、主 **Folder**（新文件、截图和产出放在这里），以及每一类访问范围各占一行。每一行显示当前的设置，点开是它自己的页面：

| 页面 | 设置什么 |
|---|---|
| **Allowed folders** | 这个工作区还能用的其他文件夹，以及各自的权限。其他工作区碰不到它们。 |
| **Sites** | 它能用哪些网站：**None**、**Listed sites** 或 **Any site**，以及[内置浏览器](../use/browser.md#allow-a-site)怎样对待每个列出的网站。 |
| **Secrets** | 它能在网络请求里发送你保存的哪些密钥。模型永远看不到密钥的值。 |
| **Scripts and commands** | 它能否运行 Python 和 Node.js **Scripts**，以及 **Commands**。 |
| **Environment variables** | 传给它的脚本和命令的值。 |

**Sites** 的几个选项是这样的：

- **None**：不能搜索网络、打开网页、下载或使用浏览器，脚本也不能联网。
- **Listed sites**：只能打开、下载、在浏览器里使用列出的网站及其子域名。搜索仍然可用；脚本不能联网。
- **Any site**：任何网站。把某个网站列出来，可以单独设定浏览器怎样使用它。

## 已允许的文件夹 {#allowed-folders}

Coscribe 在工作区主文件夹之外能用的所有文件夹，都保存在同一个列表里：**Settings › Workspaces › Manage** 下的 **Allowed folders**。列表里的每个文件夹都有权限级别（**Read only**、**Read and write** 或 **Read, write and delete**）。工作区只能碰到它在自己的 **Allowed folders** 页面上选中的那些：**Use an allowed folder** 从列表里选一个，**Add new folder…** 添加一个新的，新文件夹以读写权限加入列表。

从 **Allowed folders** 里删除一个文件夹，所有工作区都会失去它。暂时找不到的文件夹（比如拔掉的移动硬盘）会被标出来，等它回来后继续使用。

对话需要一个它碰不到的文件夹时，会用卡片来问，见[允许访问另一个文件夹](../use/approvals.md#give-access-to-another-folder)。

## 脚本和隔离 {#scripts-and-isolation}

在 Windows 上，脚本在隔离中运行：只能用对话的文件夹，不能删除或重命名其中的文件，只有工作区的 **Sites** 设为 **Any site** 时才能上网。Coscribe 会检查一次隔离在你的电脑上是否可用。如果检查没通过，脚本会被关闭；**Scripts and commands** 页面上的 **Run scripts without isolation** 可以为这个工作区重新打开它，但要承担随之而来的风险。
