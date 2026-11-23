---
title: Paramètres
description: Toutes les pages des paramètres de coscribe et le rôle de chaque paramètre.
---

Ouvrez les paramètres avec l’engrenage en haut à droite, ou avec <kbd>Ctrl</kbd> + <kbd>,</kbd> dans l’application de bureau. La zone de recherche en haut trouve un paramètre par son nom.

## General {#general}

| Paramètre | Rôle |
|---|---|
| **Theme** | Clair, sombre ou identique à Windows. |
| **Interface font** | La police des menus, panneaux et conversations : Figtree, la police du système ou OpenDyslexic. |
| **Motion** | **Reduced** réduit les animations dans les réponses en cours d’affichage et ailleurs. |
| **Conversation view** | **Simple** affiche chaque réponse sans les étapes qui la sous-tendent, avec une ligne indiquant ce que fait coscribe. **Detailed** affiche toutes les étapes. |
| **What should Coscribe call you?** | Le nom utilisé dans le message d’accueil de l’écran d’accueil. |
| **Default model** | Le modèle avec lequel démarre une nouvelle conversation. Chaque conversation peut en changer dans son propre sélecteur de modèle. |
| **Default mode** | Le [mode d’autorisation](../get-started/first-conversation.md#permission-modes) dans lequel démarre une nouvelle conversation. |
| **Global instructions** | Ce que coscribe doit toujours savoir. Voir [Instructions](../customize/instructions.md). |
| **Prompt suggestions** | Après une réponse, suggère votre prochain message dans la zone de message : <kbd>Enter</kbd> l’envoie, <kbd>Tab</kbd> le place dans la zone pour le modifier. Augmente un peu votre consommation. |
| **Background agents** | Permet à coscribe de confier du travail à des assistants qui s’exécutent en arrière-plan pendant que vous continuez à discuter. Ils peuvent consommer beaucoup. |
| **Archive inactive conversations** | Archive les conversations après 7, 30 ou 90 jours sans activité, ou jamais. Une conversation ouverte ou avec un travail en cours n’est jamais archivée. |
| **Keep running in the background** | Fermer la fenêtre laisse coscribe dans la zone de notification, et les tâches planifiées continuent de s’exécuter. Désactivé, fermer la fenêtre quitte l’application. |
| **Notifications** | **All** (toutes les exécutions de tâches), **Problems only** (une exécution a échoué ou vous attend) ou **Off**. |
| **Draw attention when Coscribe needs you** | Fait clignoter le bouton de la barre des tâches quand une réponse se termine ou que coscribe vous attend, et que la fenêtre n’est pas au premier plan. |
| **Keep computer awake while Coscribe works** | Empêche le PC de se mettre en veille pendant une réponse, pour que les longues tâches puissent se terminer. L’écran peut quand même s’éteindre, et fermer le capot met toujours le PC en veille. **Keep awake on battery power** fait de même sur batterie. |
| **Proxy** | Comment coscribe accède à Internet : **System**, **Manual** (adresse, hôtes à joindre directement, nom d’utilisateur et mot de passe) ou **No proxy**. |

## Workspaces {#workspaces}

La liste de vos [espaces de travail](../workspaces/workspaces.md) : **New** en ajoute un, et le menu **⋯** de chacun permet de le modifier ou de le supprimer. **Allowed folders** est la liste unique des dossiers situés hors du dossier principal d’un espace de travail, chacun avec son accès ; un espace de travail n’atteint que ceux qu’il choisit. Voir [Dossiers autorisés](../workspaces/workspaces.md#allowed-folders).

## Providers {#providers}

Les services de modèles que vous avez connectés et les modèles activés pour chacun. Voir [Ajouter un fournisseur de modèles](../get-started/providers.md).

## Capabilities {#capabilities}

| Paramètre | Rôle |
|---|---|
| **Create and edit files** | Permet à coscribe d’écrire et de modifier des fichiers dans les dossiers de son espace de travail. Désactivé, il se contente de les lire et répond dans la conversation. |
| **Artifacts** | Docs, designs et tableaux de bord qui s’ouvrent à côté de la conversation. Voir [Docs, designs et tableaux de bord](../office/artifacts.md). |
| **Run scripts** | Pour un travail trop lourd pour les outils intégrés, coscribe écrit un script Python ou Node.js et l’exécute après votre approbation, limité aux dossiers de l’espace de travail. Voir [Scripts et isolation](../workspaces/workspaces.md#scripts-and-isolation). |
| **Run commands** | Des lignes de commande dans cmd ou PowerShell, pour ce qu’un script ne peut pas faire, comme git ou un programme d’installation. Vous approuvez chacune. **Command sandbox** et **Private folders** définissent ce qu’une commande peut atteindre. |
| **Chats can hand tasks to Code** | Permet à une conversation de confier un travail de programmation à Codex, un agent de programmation. **Model for code** choisit son modèle ; **Change files without asking** lui permet de modifier sans demander à chaque changement. |
| **Python for scripts**, **Packages for scripts** | Quel Python exécute les scripts, et les bibliothèques Python et Node.js supplémentaires qu’ils peuvent utiliser. |
| **LibreOffice**, **Codex** | Téléchargements facultatifs, que vous installez, mettez à jour ou supprimez ici. LibreOffice produit les aperçus de pages. |

## Secrets {#secrets}

Des clés et jetons que vous ajoutez une fois, puis confiez aux espaces de travail qui en ont besoin. coscribe ne peut utiliser un secret dans une requête web que pour les hôtes que vous autorisez, et le modèle ne voit jamais sa valeur : elle est tenue à l’écart des messages, des résultats d’outils et des journaux. Les secrets sont conservés dans le Gestionnaire d’identification de Windows, jamais dans un fichier en clair.

> [!IMPORTANT]
> Cela tient la valeur à l’écart de ce que lit le modèle. Ce n’est pas une protection contre un programme qui la chercherait : tout ce que coscribe exécute sur votre PC s’exécute en votre nom et pourrait lire lui-même le coffre d’identifiants.

## Skills, Connectors, Design systems {#skills-connectors-design-systems}

Voir [Compétences et plugins](../customize/skills.md), [Connecteurs](../customize/connectors.md) et [Systèmes de design](../customize/design-systems.md).
