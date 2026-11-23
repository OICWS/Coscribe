---
title: coscribe 是什么
description: 一个运行在你电脑上的办公助手，直接做出可以编辑的 Word、Excel 和 PPT 文件。
---

coscribe 是一个装在 Windows 电脑上的 AI 办公助手。你用一句话说清楚要什么，它会读你的表格和文档，然后做出真正的成品文件：带修订和批注的合同、有图表的汇报 PPT、对好账的 Excel 表格。

它是开源软件（MIT 许可），免费使用。你只需要为自己选的模型服务付费。

## 它能做什么 {#what-it-can-do}

- **Excel**：读取、清洗、汇总、对账，写公式和图表。
- **Word**：起草和修改文档，用修订和批注标出改动，方便别人审阅。
- **PPT**：把数据和材料做成汇报，可以套用你公司的模板和配色。
- **PDF**：查找、摘录、整理内容。
- **网页**：在内置浏览器里打开网站、填表、把表格保存下来。
- **固定工作流**：一次对话做成的事，可以存成固定步骤，以后一键重跑或定时运行。

## 和其他 AI 工具有什么不同 {#how-it-differs-from-other-ai-tools}

**文件留在你的电脑上。** coscribe 没有自己的云端服务。只有模型需要读的内容会发给你选的模型服务商；如果用 Ollama 在本机跑模型，数据完全不离开电脑。

**模型随你选。** Claude、GPT、Gemini 直接支持；DeepSeek、Kimi、GLM、通义千问、豆包等任何兼容 OpenAI 接口的服务，填上地址和 API Key 就能用。详见 [添加模型服务商](providers.md)。

**改文件之前先问你。** 有四种权限模式，从“每一步都先问我”到“让审核模型替我批准日常操作”。无论哪种模式，它都只能写入你允许的文件夹。详见 [第一次对话](first-conversation.md#permission-modes)。

**做出来的是成品，不是草稿。** 每份文件写完后，coscribe 会把它渲染出来“看一眼”，检查排版和内容，而不只是交给你一段文字。

## 系统要求 {#system-requirements}

- Windows 10 或 Windows 11。
- 一个模型服务的 API Key，或者在本机运行的 Ollama / LM Studio。

> [!NOTE]
> 目前只有 Windows 版，暂不支持 Mac 和 Linux。
