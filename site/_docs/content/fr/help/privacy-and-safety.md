---
title: Confidentialité et sécurité
description: Ce qui quitte votre ordinateur quand vous utilisez Coscribe, où vos données sont conservées et ce qui encadre ses actions.
---

Coscribe fonctionne sur votre PC. Il n’a ni compte ni serveur à lui, et n’envoie rien à ses créateurs sur vous ou sur votre utilisation.

## Ce qui quitte votre ordinateur {#what-leaves-your-computer}

| Destinataire | Quoi | Quand |
|---|---|---|
| Le fournisseur de modèles que vous avez choisi | Vos messages, les parties de fichiers que Coscribe lit pour répondre et les résultats de ses outils | À chaque réponse. Avec un [modèle sur votre PC](../get-started/providers.md#run-a-model-on-your-pc), cela reste aussi sur votre ordinateur. |
| Les moteurs de recherche | Les mots recherchés | Quand Coscribe fait une recherche sur le web. Il utilise des moteurs gratuits comme DuckDuckGo, sans clé. |
| Les sites web | Des requêtes de pages ordinaires | Quand Coscribe ouvre une page que vous avez demandée ou dont une tâche a besoin. Voir [Le navigateur intégré](../use/browser.md). |
| Les services que vous avez connectés | Ce qu’envoie l’outil d’un connecteur | Quand Coscribe utilise ce [connecteur](../customize/connectors.md). |

Les conditions du fournisseur déterminent ce qu’il conserve et pendant combien de temps. Lisez-les avant de lui envoyer des documents professionnels.

## Où vos données sont conservées {#where-your-data-is-kept}

Tout le reste reste sur votre PC :

- Vos fichiers restent où ils sont ; Coscribe travaille dessus sur place.
- Les conversations, tâches planifiées, compétences et paramètres se trouvent sous `%APPDATA%\Coscribe`.
- Les clés API et les [secrets](../reference/settings.md#secrets) sont dans le Gestionnaire d’identification de Windows, jamais dans un fichier en clair.
- Un relevé du déroulement de chaque tour (le modèle, les appels d’outils, les erreurs, les jetons et la durée, sans les mots de la conversation) reste sur votre PC pour le dépannage. Rien ne l’envoie ailleurs.

## Ce qui encadre les actions {#what-keeps-actions-in-check}

- **Dossiers** : Coscribe n’écrit que dans son espace de travail et les autres dossiers que vous avez autorisés. Voir [Espaces de travail et dossiers](../workspaces/workspaces.md).
- **Approbations** : les actions qui modifient quelque chose vous attendent, selon le [mode d’autorisation](../use/approvals.md). Un fichier que Coscribe supprime avec ses propres outils de fichiers va dans la Corbeille.
- **Scripts** : ils s’exécutent dans un conteneur isolé quand Windows le permet, limités aux dossiers de l’espace de travail ; si l’isolation ne peut pas être mise en place, les scripts sont désactivés sauf si vous en décidez autrement. Voir [Scripts et isolation](../workspaces/workspaces.md#scripts-and-isolation).
- **Sites** : ce que Coscribe peut ouvrir dans le navigateur suit le réglage des sites de l’espace de travail. Voir [Autoriser un site](../use/browser.md#allow-a-site).

> [!IMPORTANT]
> Les approbations sont une vérification par vous, pas un bac à sable. Un script ou une commande que vous approuvez peut faire ce que votre compte Windows peut faire, sauf si l’isolation le retient. Lisez ce que dit une carte d’approbation avant de cliquer sur **Allow**.

## Points de vigilance {#things-to-watch-for}

- Un texte venant du web, d’un e-mail ou d’un document peut contenir des instructions destinées à une IA. Coscribe traite ce qu’il lit comme de la matière, pas comme vos ordres, mais aucun modèle n’est parfait : soyez prudent avec **Never ask** et **Auto** quand une tâche lit des contenus écrits par d’autres.
- N’ajoutez des compétences, plugins et connecteurs que de personnes de confiance.
