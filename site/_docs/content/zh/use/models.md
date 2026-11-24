---
title: 模型、思考强度和上下文
description: 为对话选择模型，设置它思考得多深，并查看它的上下文用了多少。
---

## 选择模型 {#pick-a-model}

点输入框下方的模型名称就能换模型。新模型从下一条消息开始生效，之前的对话内容都会保留。模型选择器打开时，按 <kbd>1</kbd> 到 <kbd>9</kbd> 可以选中对应编号的模型。

选择器里列出的是你在 **Settings** › **Providers** 里为各个服务商打开的模型，见[添加模型服务商](../get-started/providers.md)。新对话使用 **Settings** › **General** 里的 **Default model**。

## 设置思考强度 {#set-the-effort}

模型旁边是思考强度的控制条，从 **Faster** 到 **Smarter**。强度越高，模型思考得越久：难题上效果更好，但更慢，花费也更多。一般从 **Medium** 开始就好。

Coscribe 知道模型自己的档位时，控制条显示的就是那些档位，比如 **Low**、**Medium**、**High**、**Extra high** 和 **Max**；不知道时显示完整的刻度，模型会用它支持的最接近的档位。不支持设置强度的模型，控制条是灰色的。

换模型时你的选择会保留：新模型用它最接近的档位。

## 留意上下文 {#watch-the-context}

每个模型一次能读的内容都有上限，这就是它的上下文窗口。对话开始后，输入框旁边会出现一个圆环，显示用掉了多少。点圆环可以看到空间被什么占用：消息、系统提示、工具和技能，以及还剩多少空间。

上下文用到大约五分之四时，Coscribe 会自动把前面的对话总结一下，然后继续。你也可以输入 `/compact` 立即总结。见[让长对话继续下去](conversations.md#keep-a-long-conversation-going)。

## 控制花费 {#keep-costs-down}

模型读和写的内容都要付费给服务商。几个习惯有帮助：

- 常规工作用较低的思考强度。
- 新的工作开一个新对话，不要在很长的对话里接着做。
- 用不到的话，在 **Settings** › **General** 里关掉 **Prompt suggestions** 和 **Background agents**，它们都会增加模型调用。
- 不能离开电脑的工作，或者经常做的工作，可以用[本机上的模型](../get-started/providers.md#run-a-model-on-your-pc)，用多少次都不花钱。
