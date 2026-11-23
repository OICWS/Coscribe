---
title: Téléchargement et premier lancement
description: Téléchargez la version portable, décompressez-la, ouvrez-la et choisissez un dossier de travail.
---

coscribe ne nécessite aucune installation : téléchargez un fichier zip, décompressez-le où vous voulez et lancez-le. Il ne modifie aucun paramètre système.

## Téléchargement {#download}

1. Ouvrez la [page de publication de coscribe](https://github.com/OICWS/coscribe/releases/tag/beta) sur GitHub.
2. Sous **Assets**, téléchargez le fichier `.zip`.
3. Décompressez-le à un endroit facile à retrouver, par exemple `D:\coscribe`.

> [!NOTE]
> La version actuelle est une bêta.

## Premier lancement {#first-start}

Dans le dossier décompressé, double-cliquez sur `Coscribe.exe`.

L’application n’est pas encore signée numériquement ; la première fois que vous l’ouvrez, Windows peut donc afficher un message bleu « Windows a protégé votre ordinateur ». Cliquez sur **Informations complémentaires**, puis sur **Exécuter quand même**. Le message ne reviendra pas.

## Choisir un espace de travail {#choose-a-workspace}

Au premier lancement, coscribe vous demande de choisir un **espace de travail** (workspace) : le dossier où vous rangez vos fichiers de travail. Il propose `Documents\Coscribe` ; cliquez sur **Browse…** pour choisir un autre dossier, puis sur **Use this folder**.

L’espace de travail a deux rôles :

- Les fichiers créés par coscribe y sont enregistrés par défaut.
- Les fichiers que vous joignez à une conversation sont copiés dans son dossier `.coscribe`.

coscribe peut lire et modifier tous les fichiers de l’espace de travail. Pour passer à un autre espace de travail, ou pour donner aussi à coscribe l’accès à d’autres dossiers, utilisez le sélecteur sous la zone de message ou allez dans **Settings › Workspaces**.

## Étape suivante {#next-step}

Ensuite, [ajoutez un fournisseur de modèles](providers.md), et coscribe est prêt à travailler.
