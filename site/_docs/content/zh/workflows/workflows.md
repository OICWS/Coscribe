---
title: 工作流
description: 把一项工作存成固定步骤，按时间表或在事件发生时启动，并决定步骤出问题时 AI 能做多少主。
---

工作流是由固定步骤组成的任务。和按照写好的指令执行的定时任务不同，工作流每次都执行同样的步骤，并在运行中逐步检查，所以它做之前你就能看到它要做什么。时间表、权限和运行报告与[定时任务](scheduled-tasks.md)相同。

## 做一个工作流 {#make-a-workflow}

最简单的办法是先在对话里把工作做一遍，再把它变成工作流：

- Coscribe 提示 **Save this job?** 时选 **Save as workflow**，或者在 **Task details** 面板里选。
- 或者在输入框里输入 `/saveworkflow`，后面可以跟一个名字。

Coscribe 会根据对话起草步骤。检查一遍，然后保存。

也可以从零开始：**Scheduled** › **New task** › **Build a workflow**。起个名字、定好时间表，保存后在它的页面上添加步骤。

## 工作流页面 {#the-workflow-page}

页面有四个标签：

- **Overview** 用平实的话说明工作流做什么：什么时候运行、处理什么、在哪里停下来等你、能碰到什么。**Show the flowchart** 会画出步骤。
- **Steps** 列出所有步骤，在这里添加、修改和调整顺序。也可以切换成 **Flowchart** 视图。
- **Runs** 列出以往的运行。
- **Settings** 放时间表、工作区和权限。

工作流还没有步骤时，**Run now** 是灰色的。如果工作流需要输入（比如一个文件），它会先问你要。

## 步骤的种类 {#kinds-of-steps}

**Add a step** 提供这些种类：

| 步骤 | 做什么 |
|---|---|
| **Tool** | 使用 Coscribe 的一个工具，不经过模型。 |
| **Script** | 运行一段你审阅过的固定 Python 脚本。 |
| **Model** | 一次模型调用，必须返回指定的字段。 |
| **Agent** | 在你设定的范围内用工具完成一个目标：它能调用的工具、能修改的文件夹、能打开的网站。 |
| **Check** | 除非某些值成立，否则停止运行。 |
| **Approval** | 暂停，直到你批准。 |
| **Ask you** | 暂停，直到你填好后面步骤要用的值。 |
| **Wait** | 暂停一段时间、等到某个时刻，或者等某个文件出现。 |
| **Remember** | 为下次运行保存一个值，比如已经处理过哪些。 |
| **Run a task** | 把你的另一个任务当作一步来运行，并使用它的结果。 |
| **If / otherwise** | 根据一个值运行不同的步骤。 |
| **Choose a path** | 几条路径，按一个值是什么来选。 |
| **At the same time** | 同时运行 2 到 6 条步骤线，然后继续。 |
| **For each** | 对列表里的每一项重复执行步骤。 |

每一步都可以设定失败时怎么办：**Stop the run**、**Skip it and go on** 或 **Run other steps instead**。一步也可以设定重试的次数。

## 步骤出问题时 {#autonomy}

网站会改版，每次的文件也不一样。**If a step stops working** 这个设置决定出问题时 AI 能做多少主：

| 级别 | 会怎样 |
|---|---|
| **Fixed** | 只运行保存好的步骤。某一步失败，运行就停下并告诉你。 |
| **Self-healing** | 网站改了版，AI 按页面现在的样子完成那一步。 |
| **Proactive** | AI 步骤自己决定怎么完成它那部分。某一步失败时，AI 可以加几步；会改动东西的步骤要等你同意。 |
| **Autonomous** | AI 可以按自己的方式完成整个任务。 |

运行中绕过了某个变化之后，Coscribe 可以给出更新后的步骤供你审阅，这样下次运行就不用再绕了。

## 在事件发生时启动工作流 {#start-on-an-event}

除了所有任务都有的时间表，工作流的 **Frequency** 还可以是：

- **Every few minutes**：每隔几分钟。
- **When a file arrives in a folder**：选择 **Folder to watch**，需要的话再填一个 **File name pattern**。每来一个新文件就启动一次运行，这个文件作为工作流的文件输入。这个选项要求工作流有一个文件输入。
- **When something new shows up in a connector**：选一个连接器，以及要问它什么。Coscribe 每隔几分钟问一次，每出现一个新条目就启动一次运行。第一次检查会把已有的内容当作已经看过。
- **When a program sends it an event**：同一台电脑上的另一个程序带着密钥，向 Coscribe 显示的地址发送请求。**Wait for a sample** 会保留下一个事件，让你选出它的哪些字段填入输入。这个地址只接受来自你自己电脑的请求。

Coscribe 关闭期间到达的文件，会在 Coscribe 再次启动时启动运行。
