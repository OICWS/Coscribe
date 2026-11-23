---
title: 添加模型服务商
description: 填入一个模型服务的 API Key，选好要用的模型。
---

coscribe 本身不带模型。它调用你选择的模型服务来思考和写作，所以开始之前需要添加至少一个 **服务商**（provider），并填入你在那家服务开的 API Key。

## 添加一个服务商 {#add-a-provider}

1. 点窗口右上角的齿轮图标打开 **Settings**，进入 **Providers**。
2. 在列表里找到你要用的服务，点它打开设置页。没有现成的，就选 **Custom provider**。
3. 在 **API key** 里粘贴你的 Key。还没有 Key 的话，点 **Get an API key** 会打开那家服务的申请页面。
4. 列出可用的模型后，打开你想用的模型（至少要打开一个），再选一个 **Default model**（默认模型）。
5. 点 **Add provider** 保存。

> [!IMPORTANT]
> API Key 只保存在你自己的电脑上（通常存放在 Windows 凭据管理器里），模型看不到它，聊天记录里也不会出现。

## 可以用哪些服务 {#which-services-you-can-use}

| 类型 | 服务 |
|---|---|
| 内置支持 | Anthropic（Claude）、OpenAI（GPT）、Google Gemini |
| 国内服务 | DeepSeek、Kimi、GLM（智谱）、Qwen（阿里云百炼）、Doubao（火山方舟）、MiniMax、SiliconFlow（硅基流动） |
| 国外服务 | OpenRouter、Mistral AI、xAI、Groq、Together AI、Fireworks AI、Cerebras |
| 在本机运行 | Ollama、LM Studio |

列表里没有的服务，只要兼容 OpenAI 的接口，都可以用 **Custom provider** 添加：填一个名字、服务的 **Base URL**（接口地址）和 API Key 即可。

## 在本机运行模型 {#run-a-model-on-your-pc}

如果你不希望任何内容离开电脑，可以先安装 [Ollama](https://ollama.com) 或 [LM Studio](https://lmstudio.ai) 并下载一个模型，再在 Providers 里选 **On this computer** 下面对应的一项。这种方式不产生 API 费用，但对电脑配置要求较高，效果取决于你下载的模型。

## 换一个模型 {#switch-models}

每个对话都可以单独换模型：点输入框下方的模型名称，从列表里选。新对话默认用哪个模型，在 **Settings › General** 的 **Default model** 里设置。
