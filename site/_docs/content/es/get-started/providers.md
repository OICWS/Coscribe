---
title: Añadir un proveedor de modelos
description: Introduce una clave de API de un servicio de modelos y elige los modelos que vas a usar.
---

coscribe no tiene un modelo propio. Llama al servicio de modelos que elijas para pensar y escribir, así que antes de empezar añade al menos un **proveedor** e introduce la clave de API que te dio ese servicio.

## Añadir un proveedor {#add-a-provider}

1. Haz clic en el engranaje arriba a la derecha de la ventana para abrir **Settings** y ve a **Providers**.
2. Busca el servicio que quieres en la lista y haz clic para abrir su página. Si no aparece, elige **Custom provider**.
3. Pega tu clave en **API key**. ¿Aún no tienes clave? **Get an API key** abre la página del servicio para crear una.
4. Cuando aparezcan los modelos, activa los que quieras (al menos uno) y elige un **Default model**.
5. Haz clic en **Add provider** para guardar.

> [!IMPORTANT]
> Tu clave de API solo se guarda en tu propio PC (normalmente en el Administrador de credenciales de Windows). El modelo no puede verla y nunca aparece en una conversación.

## Qué servicios puedes usar {#which-services-you-can-use}

| Tipo | Servicios |
|---|---|
| Integrados | Anthropic (Claude), OpenAI (GPT), Google Gemini |
| China | DeepSeek, Kimi, GLM (Zhipu), Qwen (Alibaba Cloud Model Studio), Doubao (Volcano Engine Ark), MiniMax, SiliconFlow |
| Otros | OpenRouter, Mistral AI, xAI, Groq, Together AI, Fireworks AI, Cerebras |
| En tu PC | Ollama, LM Studio |

Cualquier otro servicio con una API compatible con OpenAI se puede añadir como **Custom provider**: introduce un nombre, la **Base URL** del servicio y tu clave de API.

## Ejecutar un modelo en tu PC {#run-a-model-on-your-pc}

Si quieres que nada salga de tu ordenador, instala [Ollama](https://ollama.com) o [LM Studio](https://lmstudio.ai), descarga un modelo y elígelo en **On this computer** dentro de Providers. No cuesta nada por uso, pero necesita un PC potente, y los resultados dependen del modelo que descargues.

## Cambiar de modelo {#switch-models}

Cada conversación puede usar su propio modelo: haz clic en el nombre del modelo bajo el cuadro de mensaje y elige uno. El modelo con el que empieza una conversación nueva es el **Default model** de **Settings › General**.
