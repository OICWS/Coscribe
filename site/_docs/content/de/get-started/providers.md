---
title: Einen Modellanbieter hinzufügen
description: Geben Sie einen API-Schlüssel für einen Modelldienst ein und wählen Sie die Modelle, die Sie nutzen möchten.
---

Coscribe hat kein eigenes Modell. Zum Denken und Schreiben ruft es den Modelldienst auf, den Sie wählen. Fügen Sie daher vor dem Start mindestens einen **Anbieter** (Provider) hinzu und geben Sie den API-Schlüssel ein, den Sie von diesem Dienst erhalten haben.

## Einen Anbieter hinzufügen {#add-a-provider}

1. Klicken Sie oben rechts im Fenster auf das Zahnradsymbol, um **Settings** zu öffnen, und gehen Sie zu **Providers**.
2. Suchen Sie den gewünschten Dienst in der Liste und klicken Sie darauf, um seine Seite zu öffnen. Steht er nicht in der Liste, wählen Sie **Custom provider**.
3. Fügen Sie Ihren Schlüssel in **API key** ein. Noch keinen Schlüssel? **Get an API key** öffnet die Seite des Dienstes, auf der Sie einen erstellen.
4. Sobald die Modelle aufgelistet sind, schalten Sie die gewünschten ein (mindestens eines) und wählen Sie ein **Default model**.
5. Klicken Sie auf **Add provider**, um zu speichern.

> [!IMPORTANT]
> Ihr API-Schlüssel wird nur auf Ihrem eigenen PC gespeichert (normalerweise in der Windows-Anmeldeinformationsverwaltung). Das Modell kann ihn nicht sehen, und er erscheint nie in einer Unterhaltung.

## Welche Dienste Sie nutzen können {#which-services-you-can-use}

| Art | Dienste |
|---|---|
| Integriert | Anthropic (Claude), OpenAI (GPT), Google Gemini |
| China | DeepSeek, Kimi, GLM (Zhipu), Qwen (Alibaba Cloud Model Studio), Doubao (Volcano Engine Ark), MiniMax, SiliconFlow |
| Weitere | OpenRouter, Mistral AI, xAI, Groq, Together AI, Fireworks AI, Cerebras |
| Auf Ihrem PC | Ollama, LM Studio |

Jeder andere Dienst mit einer OpenAI-kompatiblen API lässt sich als **Custom provider** hinzufügen: Geben Sie einen Namen, die **Base URL** des Dienstes und Ihren API-Schlüssel ein.

## Ein Modell auf Ihrem PC ausführen {#run-a-model-on-your-pc}

Wenn nichts Ihren Computer verlassen soll, installieren Sie [Ollama](https://ollama.com) oder [LM Studio](https://lmstudio.ai), laden ein Modell herunter und wählen es unter **On this computer** in Providers. Das kostet nichts pro Nutzung, braucht aber einen leistungsfähigen PC, und die Ergebnisse hängen vom heruntergeladenen Modell ab.

## Modell wechseln {#switch-models}

Jede Unterhaltung kann ihr eigenes Modell verwenden: Klicken Sie unter dem Nachrichtenfeld auf den Modellnamen und wählen Sie eines. Das Modell, mit dem eine neue Unterhaltung beginnt, ist das **Default model** unter **Settings › General**.
