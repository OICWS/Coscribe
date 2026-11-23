---
title: Ajouter un fournisseur de modèles
description: Saisissez la clé API d’un service de modèles et choisissez les modèles à utiliser.
---

Coscribe n’a pas de modèle à lui. Pour réfléchir et écrire, il fait appel au service de modèles que vous choisissez ; avant de commencer, ajoutez donc au moins un **fournisseur** (provider) et saisissez la clé API obtenue auprès de ce service.

## Ajouter un fournisseur {#add-a-provider}

1. Cliquez sur l’icône d’engrenage en haut à droite de la fenêtre pour ouvrir **Settings**, puis allez dans **Providers**.
2. Trouvez le service voulu dans la liste et cliquez dessus pour ouvrir sa page. S’il n’y figure pas, choisissez **Custom provider**.
3. Collez votre clé dans **API key**. Pas encore de clé ? **Get an API key** ouvre la page du service où en créer une.
4. Une fois les modèles affichés, activez ceux que vous voulez (au moins un), puis choisissez un **Default model**.
5. Cliquez sur **Add provider** pour enregistrer.

> [!IMPORTANT]
> Votre clé API est conservée uniquement sur votre PC (normalement dans le Gestionnaire d’identification de Windows). Le modèle ne peut pas la voir, et elle n’apparaît jamais dans une conversation.

## Services utilisables {#which-services-you-can-use}

| Type | Services |
|---|---|
| Intégrés | Anthropic (Claude), OpenAI (GPT), Google Gemini |
| Chine | DeepSeek, Kimi, GLM (Zhipu), Qwen (Alibaba Cloud Model Studio), Doubao (Volcano Engine Ark), MiniMax, SiliconFlow |
| Ailleurs | OpenRouter, Mistral AI, xAI, Groq, Together AI, Fireworks AI, Cerebras |
| Sur votre PC | Ollama, LM Studio |

Tout autre service doté d’une API compatible OpenAI peut être ajouté comme **Custom provider** : saisissez un nom, la **Base URL** du service et votre clé API.

## Exécuter un modèle sur votre PC {#run-a-model-on-your-pc}

Si vous ne voulez rien laisser sortir de votre ordinateur, installez [Ollama](https://ollama.com) ou [LM Studio](https://lmstudio.ai), téléchargez un modèle, puis choisissez-le sous **On this computer** dans Providers. Rien n’est facturé à l’usage, mais il faut un PC puissant, et les résultats dépendent du modèle téléchargé.

## Changer de modèle {#switch-models}

Chaque conversation peut utiliser son propre modèle : cliquez sur le nom du modèle sous la zone de message et choisissez-en un. Le modèle avec lequel démarre une nouvelle conversation est le **Default model** de **Settings › General**.
