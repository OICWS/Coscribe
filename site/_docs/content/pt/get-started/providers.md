---
title: Adicionar um provedor de modelos
description: Informe uma chave de API de um serviço de modelos e escolha os modelos que vai usar.
---

O coscribe não tem modelo próprio. Ele chama o serviço de modelos que você escolher para pensar e escrever; por isso, antes de começar, adicione pelo menos um **provedor** e informe a chave de API que você obteve desse serviço.

## Adicionar um provedor {#add-a-provider}

1. Clique no ícone de engrenagem no canto superior direito da janela para abrir **Settings** e vá até **Providers**.
2. Encontre na lista o serviço que deseja e clique nele para abrir sua página. Se ele não estiver na lista, escolha **Custom provider**.
3. Cole sua chave em **API key**. Ainda não tem uma? **Get an API key** abre a página do serviço para criar uma.
4. Quando os modelos aparecerem, ative os que quiser (pelo menos um) e escolha um **Default model**.
5. Clique em **Add provider** para salvar.

> [!IMPORTANT]
> Sua chave de API fica guardada apenas no seu PC (normalmente no Gerenciador de Credenciais do Windows). O modelo não consegue vê-la, e ela nunca aparece em uma conversa.

## Quais serviços você pode usar {#which-services-you-can-use}

| Tipo | Serviços |
|---|---|
| Integrados | Anthropic (Claude), OpenAI (GPT), Google Gemini |
| China | DeepSeek, Kimi, GLM (Zhipu), Qwen (Alibaba Cloud Model Studio), Doubao (Volcano Engine Ark), MiniMax, SiliconFlow |
| Outros | OpenRouter, Mistral AI, xAI, Groq, Together AI, Fireworks AI, Cerebras |
| No seu PC | Ollama, LM Studio |

Qualquer outro serviço com uma API compatível com a da OpenAI pode ser adicionado como **Custom provider**: informe um nome, a **Base URL** do serviço e sua chave de API.

## Executar um modelo no seu PC {#run-a-model-on-your-pc}

Se você não quer que nada saia do seu computador, instale o [Ollama](https://ollama.com) ou o [LM Studio](https://lmstudio.ai), baixe um modelo e escolha-o em **On this computer**, na página Providers. Não há custo por uso, mas é preciso um PC potente, e os resultados dependem do modelo que você baixar.

## Trocar de modelo {#switch-models}

Cada conversa pode usar seu próprio modelo: clique no nome do modelo abaixo da caixa de mensagem e escolha um. O modelo com que uma nova conversa começa é o **Default model**, em **Settings › General**.
