---
title: 下载和第一次启动
description: 下载免安装版，解压后打开，选一个工作文件夹。
---

coscribe 是免安装的：下载一个压缩包，解压到任意位置就能用，不会改动系统设置。

## 下载

1. 打开 GitHub 上的 [coscribe 发布页](https://github.com/OICWS/coscribe/releases/tag/beta)。
2. 在 **Assets** 下面下载 `.zip` 文件。
3. 把它解压到你方便找到的地方，比如 `D:\coscribe`。

> [!NOTE]
> 现在发布的是测试版（beta）。

## 第一次打开

在解压出来的文件夹里双击 `Coscribe.exe`。

coscribe 的安装包还没有数字签名，所以第一次打开时，Windows 可能会弹出蓝色的“Windows 已保护你的电脑”提示。点 **更多信息**，再点 **仍要运行** 即可。之后再打开就不会提示了。

## 选择工作区

第一次启动时，coscribe 会请你选一个 **工作区**：你平时放工作文件的文件夹。默认建议的是 `文档\Coscribe`，你也可以点 **Browse…** 换成别的文件夹，然后点 **Use this folder**。

工作区有两个作用：

- coscribe 做出来的文件默认保存在这里。
- 你在对话里附上的文件，会复制一份到工作区里的 `.coscribe` 文件夹。

coscribe 可以读写工作区里的所有文件。以后需要换工作区，或者让它也能访问别的文件夹，可以在输入框下方切换，或者到 **Settings › Workspaces** 里设置。

## 下一步

接下来 [添加一个模型服务商](providers.md)，coscribe 就可以开始工作了。
