---
title: What is Coscribe
description: An office assistant that runs on your PC and makes Word, Excel and PowerPoint files you can edit.
---

Coscribe is an AI office assistant for Windows. Say in a sentence what you need, and it reads your spreadsheets and documents and makes the finished file: a contract with tracked changes and comments, a report deck with charts, a reconciled Excel workbook.

It is open source (MIT license) and free to use. You pay only for the model service you choose.

## What it can do

- **Excel**: read, clean, summarize and reconcile data; write formulas and charts.
- **Word**: draft and revise documents, marking changes with tracked changes and comments so others can review them.
- **PowerPoint**: turn data and material into a presentation, using your company's template and colors if you have them.
- **PDF**: search, extract and organize content.
- **The web**: open sites in a built-in browser, fill in forms and save tables.
- **Workflows**: save what a conversation did as fixed steps, then rerun it with one click or on a schedule.

## How it differs from other AI tools

**Your files stay on your PC.** Coscribe has no cloud service of its own. Only what the model needs to read goes to the model provider you chose; with a model running on your own computer through Ollama, nothing leaves the machine.

**You choose the model.** Claude, GPT and Gemini are built in. DeepSeek, Kimi, GLM, Qwen, Doubao and any other service with an OpenAI-compatible API work once you enter its address and API key. See [Add a model provider](providers.md).

**It asks before it changes things.** Four permission modes range from "ask me before every step" to "let a reviewer model approve routine work for me". In every mode it writes only to the folders you allowed. See [Your first conversation](first-conversation.md#permission-modes).

**It hands you finished files, not drafts.** After writing a file, Coscribe renders it and looks at the result to check the layout and content, rather than handing you a block of text.

## System requirements

- Windows 10 or Windows 11.
- An API key from a model service, or Ollama or LM Studio running on your PC.

> [!NOTE]
> Coscribe is available for Windows only. There is no Mac or Linux version yet.
