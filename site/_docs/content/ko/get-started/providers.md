---
title: 모델 공급자 추가
description: 모델 서비스의 API 키를 입력하고 사용할 모델을 고릅니다.
---

Coscribe에는 자체 모델이 없습니다. 생각하고 글을 쓸 때 사용자가 고른 모델 서비스를 호출하므로, 시작하기 전에 **공급자**(provider)를 하나 이상 추가하고 그 서비스에서 받은 API 키를 입력하세요.

## 공급자 추가하기 {#add-a-provider}

1. 창 오른쪽 위의 톱니바퀴 아이콘을 클릭해 **Settings**를 열고 **Providers**로 갑니다.
2. 목록에서 원하는 서비스를 찾아 클릭하면 해당 페이지가 열립니다. 목록에 없으면 **Custom provider**를 선택합니다.
3. **API key**에 키를 붙여 넣습니다. 아직 키가 없다면 **Get an API key**가 키를 만드는 서비스 페이지를 엽니다.
4. 모델 목록이 나타나면 원하는 모델을 켜고(하나 이상) **Default model**을 고릅니다.
5. **Add provider**를 클릭해 저장합니다.

> [!IMPORTANT]
> API 키는 사용자의 PC에만 보관됩니다(보통 Windows 자격 증명 관리자). 모델은 키를 볼 수 없으며, 대화에 나타나지도 않습니다.

## 사용할 수 있는 서비스 {#which-services-you-can-use}

| 종류 | 서비스 |
|---|---|
| 기본 제공 | Anthropic (Claude), OpenAI (GPT), Google Gemini |
| 중국 | DeepSeek, Kimi, GLM (Zhipu), Qwen (Alibaba Cloud Model Studio), Doubao (Volcano Engine Ark), MiniMax, SiliconFlow |
| 기타 | OpenRouter, Mistral AI, xAI, Groq, Together AI, Fireworks AI, Cerebras |
| 내 PC | Ollama, LM Studio |

OpenAI 호환 API를 제공하는 다른 서비스도 **Custom provider**로 추가할 수 있습니다. 이름, 서비스의 **Base URL**, API 키를 입력하세요.

## 내 PC에서 모델 실행하기 {#run-a-model-on-your-pc}

아무것도 컴퓨터 밖으로 나가지 않게 하려면 [Ollama](https://ollama.com)나 [LM Studio](https://lmstudio.ai)를 설치하고 모델을 다운로드한 뒤, Providers의 **On this computer**에서 고르세요. 사용료는 들지 않지만 성능 좋은 PC가 필요하고, 결과는 다운로드한 모델에 따라 달라집니다.

## 모델 바꾸기 {#switch-models}

대화마다 다른 모델을 쓸 수 있습니다. 메시지 상자 아래의 모델 이름을 클릭해 고르세요. 새 대화가 처음 쓰는 모델은 **Settings › General**의 **Default model**입니다.
