---
title: モデルプロバイダーを追加する
description: モデルサービスの API キーを入力し、使うモデルを選びます。
---

coscribe には独自のモデルがありません。考えたり書いたりするときは、選んだモデルサービスを呼び出します。始める前に、少なくとも 1 つの **プロバイダー** を追加し、そのサービスで取得した API キーを入力してください。

## プロバイダーを追加する {#add-a-provider}

1. ウィンドウ右上の歯車アイコンをクリックして **Settings** を開き、**Providers** に進みます。
2. 一覧から使いたいサービスを探し、クリックしてそのページを開きます。一覧にない場合は **Custom provider** を選びます。
3. **API key** にキーを貼り付けます。キーがまだない場合は、**Get an API key** でサービスのキー作成ページが開きます。
4. モデルが一覧表示されたら、使いたいもの（1 つ以上）をオンにし、**Default model** を選びます。
5. **Add provider** をクリックして保存します。

> [!IMPORTANT]
> API キーは自分の PC にだけ保存されます（通常は Windows の資格情報マネージャー）。モデルからは見えず、会話に表示されることもありません。

## 使えるサービス {#which-services-you-can-use}

| 種類 | サービス |
|---|---|
| 組み込み | Anthropic (Claude)、OpenAI (GPT)、Google Gemini |
| 中国 | DeepSeek、Kimi、GLM (Zhipu)、Qwen (Alibaba Cloud Model Studio)、Doubao (Volcano Engine Ark)、MiniMax、SiliconFlow |
| その他 | OpenRouter、Mistral AI、xAI、Groq、Together AI、Fireworks AI、Cerebras |
| PC 上 | Ollama、LM Studio |

OpenAI 互換 API を持つほかのサービスは **Custom provider** として追加できます。名前、サービスの **Base URL**、API キーを入力します。

## PC でモデルを動かす {#run-a-model-on-your-pc}

何も PC の外に出したくない場合は、[Ollama](https://ollama.com) か [LM Studio](https://lmstudio.ai) をインストールしてモデルをダウンロードし、Providers の **On this computer** から選びます。利用ごとの費用はかかりませんが、性能の高い PC が必要で、結果はダウンロードしたモデル次第です。

## モデルを切り替える {#switch-models}

会話ごとに別のモデルを使えます。メッセージ欄の下にあるモデル名をクリックして選んでください。新しい会話で最初に使われるモデルは、**Settings › General** の **Default model** です。
