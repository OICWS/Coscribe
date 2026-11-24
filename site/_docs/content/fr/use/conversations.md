---
title: Travailler dans une conversation
description: Envoyez des messages et des fichiers, complétez une demande pendant que Coscribe travaille, arrêtez-le, et annulez ou modifiez ce que vous avez envoyé.
---

Tout commence dans une conversation. Chacune a son propre historique, son modèle, son mode d’autorisation et ses dossiers.

## Envoyer des messages et des fichiers {#send-messages-and-files}

Tapez dans la zone de message et appuyez sur <kbd>Enter</kbd>. Pour joindre un fichier ou une image, cliquez sur **+** en bas à gauche de la zone de message ou faites-le glisser dans la fenêtre. Les fichiers joints sont enregistrés dans le dossier `.coscribe/uploads/` de l’espace de travail, pour que Coscribe puisse les rouvrir plus tard.

## Compléter une demande en cours {#add-to-a-request-while-it-works}

Vous n’avez pas besoin d’attendre la fin d’une réponse. Tout ce que vous envoyez pendant que Coscribe travaille devient une note qu’il lit avant son étape suivante, images et fichiers compris. Une note en attente a ses propres boutons :

- **Send now** l’envoie immédiatement.
- **Cancel and edit message** la remet dans la zone de message. Ce n’est possible que si la zone de message est vide.

Quand Coscribe attend une réponse à une carte (une question ou une approbation), ce que vous tapez répond à cette carte : une réponse tapée à une question est votre réponse, et une réponse tapée à une approbation refuse l’action et explique pourquoi à Coscribe.

## Arrêter une réponse {#stop-a-reply}

Cliquez sur **Stop** à droite de la zone de message. Tout ce que Coscribe a déjà écrit et fait est conservé, et la réponse se termine par « Stopped · What should I do instead? ». Il ne reprend pas le travail arrêté sauf si vous le lui demandez.

Arrêter une réponse n’arrête pas les scripts ni les commandes qu’elle a laissés tourner en arrière-plan ; la ligne sous la réponse indique combien sont encore en cours et ouvre le panneau **Background tasks**, où vous pouvez les arrêter.

## Revenir en arrière ou modifier un message {#rewind-or-edit-a-message}

Survolez un message que vous avez envoyé pour voir quand vous l’avez envoyé et trois boutons :

- **Rewind to here** supprime ce message et tout ce qui suit, et remet son texte dans la zone de message.
- **Edit** vous permet de modifier le message ; **Save** supprime les tours suivants et envoie le nouveau texte.
- **Copy** copie le texte.

> [!WARNING]
> Revenir en arrière supprime des tours de la conversation, pas leurs effets. Un fichier écrit par Coscribe, une commande qu’il a exécutée ou un message qu’il a envoyé via un connecteur restent tels quels. L’info-bulle vous prévient quand un tour que vous allez supprimer a fait l’une de ces choses.

Rewind et Edit ne sont pas disponibles pendant qu’une réponse est en cours ou qu’une carte vous attend, ni pour les messages antérieurs à un `/compact`.

## Copier une conversation {#copy-a-conversation}

Tapez `/fork` pour copier la conversation dans une nouvelle et l’ouvrir ; `/fork Brouillon T3 B` nomme la copie. Les deux conversations repartent du même point et travaillent sur les mêmes fichiers : un fichier modifié depuis l’une l’est aussi pour l’autre.

## Poursuivre une longue conversation {#keep-a-long-conversation-going}

Chaque modèle ne peut lire qu’une quantité limitée à la fois. Quand une conversation devient longue, tapez `/compact` : Coscribe la résume pour libérer de la place et continue. `/clear` archive la conversation et en démarre une nouvelle dans le même espace de travail.

## Poser une question à part {#ask-a-side-question}

Le panneau **Side chat** (les deux bulles dans la barre d’outils) répond à des questions sur la conversation sans rien y ajouter, même pendant qu’une réponse est en cours. Il voit la conversation telle qu’elle est à cet instant. Ses messages ne sont conservés que tant que le panneau est ouvert.

## Vue simple ou détaillée {#simple-or-detailed-view}

Par défaut, une conversation affiche chaque étape de Coscribe. Dans **Settings › General**, réglez **Conversation view** sur **Simple** pour ne voir que la réponse et une ligne indiquant ce que fait Coscribe, par exemple « Reading » ou « Running commands ». Les cartes qui ont besoin de vous, comme les approbations et les questions, s’affichent dans les deux vues, et revenir à **Detailed** réaffiche toutes les étapes.
