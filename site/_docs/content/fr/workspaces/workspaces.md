---
title: Espaces de travail et dossiers
description: Décidez quels dossiers, sites, secrets et scripts chaque conversation peut atteindre.
---

Un **espace de travail** (workspace) est le dossier dans lequel travaille une conversation, avec ce qu’elle peut atteindre au-delà : d’autres dossiers, des sites web, des secrets et des scripts. Chaque conversation utilise un espace de travail. Les conversations qui n’en choisissent pas utilisent l’espace de travail **Default**.

## Choisir l’espace de travail d’une conversation {#pick-a-workspace-for-a-conversation}

Utilisez le sélecteur d’espace de travail sous la zone de message. Il liste vos espaces de travail et propose **New workspace**. L’espace de travail **Default** est utilisé par toute conversation qui n’en a pas choisi un autre.

## Modifier un espace de travail {#edit-a-workspace}

Ouvrez **Settings › Workspaces** et choisissez **Edit** dans le menu **⋯** d’un espace de travail, ou créez-en un avec **New**. La boîte de dialogue comporte un nom, le dossier principal **Folder** (les nouveaux fichiers, les captures d’écran et les artefacts y sont enregistrés) et une ligne par type d’accès. Chaque ligne affiche le réglage actuel et ouvre sa propre page :

| Page | Ce qu’elle règle |
|---|---|
| **Allowed folders** | Les autres dossiers que cet espace de travail peut utiliser, chacun avec son accès. Les autres espaces de travail ne les atteignent pas. |
| **Sites** | Les sites web qu’il peut utiliser : **None**, **Listed sites** ou **Any site**, et la façon dont le [navigateur intégré](../use/browser.md#allow-a-site) traite chaque site listé. |
| **Secrets** | Lesquels de vos secrets enregistrés il peut envoyer dans une requête web. Le modèle ne voit jamais la valeur d’un secret. |
| **Scripts and commands** | S’il peut exécuter des **Scripts** Python et Node.js, et des **Commands**. |
| **Environment variables** | Des valeurs transmises à ses scripts et commandes. |

Ce que signifie le choix **Sites** :

- **None** : pas de recherche web, de pages web, de téléchargements ni d’étapes dans le navigateur, et les scripts restent hors ligne.
- **Listed sites** : il ouvre, télécharge depuis et utilise dans le navigateur uniquement les sites listés et leurs sous-domaines. La recherche fonctionne toujours ; les scripts restent hors ligne.
- **Any site** : n’importe quel site. Ajoutez un site à la liste pour choisir comment le navigateur l’utilise.

## Dossiers autorisés {#allowed-folders}

Tous les dossiers que coscribe peut utiliser hors du dossier principal d’un espace de travail figurent dans une seule liste, **Allowed folders**, sous **Settings › Workspaces › Manage**. Chaque dossier y a un niveau d’accès (**Read only**, **Read and write** ou **Read, write and delete**). Un espace de travail n’atteint que les dossiers autorisés qu’il choisit sur sa page **Allowed folders** : **Use an allowed folder** en choisit un dans la liste, et **Add new folder…** en ajoute un nouveau, qui rejoint la liste en lecture et écriture.

Retirer un dossier de **Allowed folders** le retire de tous les espaces de travail. Un dossier introuvable pour le moment, comme un lecteur débranché, est signalé et réutilisé quand il revient.

Quand une conversation a besoin d’un dossier qu’elle ne peut pas atteindre, elle le demande sur une carte ; voir [Donner accès à un autre dossier](../use/approvals.md#give-access-to-another-folder).

## Scripts et isolation {#scripts-and-isolation}

Sous Windows, les scripts s’exécutent isolés : ils ne peuvent utiliser que les dossiers de la conversation, ne peuvent pas y supprimer ni renommer de fichiers, et n’accèdent à Internet que si le paramètre **Sites** de l’espace de travail est **Any site**. coscribe vérifie une fois si l’isolation fonctionne sur votre ordinateur. Si la vérification a échoué, les scripts sont désactivés ; **Run scripts without isolation**, sur la page **Scripts and commands**, les réactive pour cet espace de travail, avec le risque que cela comporte.
