---
title: Add a model provider
description: Enter an API key for a model service and choose the models to use.
---

coscribe has no model of its own. It calls the model service you choose to think and write, so before you start, add at least one **provider** and enter the API key you got from that service.

## Add a provider

1. Click the gear icon at the top right of the window to open **Settings**, then go to **Providers**.
2. Find the service you want in the list and click it to open its page. If it isn't listed, choose **Custom provider**.
3. Paste your key into **API key**. No key yet? **Get an API key** opens the service's page for creating one.
4. Once the models are listed, turn on the ones you want (at least one), then choose a **Default model**.
5. Click **Add provider** to save.

> [!IMPORTANT]
> Your API key is kept only on your own PC (normally in Windows Credential Manager). The model can't see it, and it never appears in a conversation.

## Which services you can use

| Kind | Services |
|---|---|
| Built in | Anthropic (Claude), OpenAI (GPT), Google Gemini |
| China | DeepSeek, Kimi, GLM (Zhipu), Qwen (Alibaba Cloud Model Studio), Doubao (Volcano Engine Ark), MiniMax, SiliconFlow |
| Elsewhere | OpenRouter, Mistral AI, xAI, Groq, Together AI, Fireworks AI, Cerebras |
| On your PC | Ollama, LM Studio |

Any other service with an OpenAI-compatible API can be added as a **Custom provider**: enter a name, the service's **Base URL** and your API key.

## Run a model on your PC

If you want nothing to leave your computer, install [Ollama](https://ollama.com) or [LM Studio](https://lmstudio.ai) and download a model, then pick it under **On this computer** in Providers. This costs nothing per use, but it needs a capable PC, and the results depend on the model you download.

## Switch models

Each conversation can use its own model: click the model name below the message box and pick one. The model a new conversation starts with is the **Default model** under **Settings › General**.
