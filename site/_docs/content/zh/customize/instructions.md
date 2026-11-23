---
title: 指令
description: 把 coscribe 应该一直知道的事告诉它一次，适用于所有对话或某一个文件夹。
---

指令是 coscribe 每次开始处理你的请求之前都会读的常设说明，这样你就不用一遍遍重复。

## 适用于所有对话 {#for-every-conversation}

打开 **Settings** › **General**，在 **Global instructions** 里写下 coscribe 应该一直知道的偏好、惯例或背景。比如公司名称、你用的日期格式，或者报告一律用英文。它们适用于每个新对话，而且只有你能修改，coscribe 自己改不了。

## 适用于一个文件夹 {#for-one-folder}

为某个文件夹写的说明，放在它里面的 `.coscribe/memory.md`：文件夹的用途、惯例、常用的名称。你接受这个文件夹的设置之后，coscribe 每次在这个文件夹里开始对话都会读它。见[文件夹自己的说明和规则](../workspaces/folder-settings.md)。

## 让 coscribe 描述一个文件夹 {#have-coscribe-describe-a-folder}

在对话里输入 `/init`，coscribe 会浏览工作区，在根目录写一个 `OVERVIEW.md`：文件夹里有什么、是怎么组织的。以后再运行一次就会更新这个文件。

## 你的名字 {#your-name}

**Settings** › **General** 里的 **What should Coscribe call you?** 设置首页问候语里用的名字。
