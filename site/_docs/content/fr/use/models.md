---
title: Modèles, effort et contexte
description: Choisissez le modèle d’une conversation, réglez son niveau de réflexion et voyez à quel point son contexte est rempli.
---

## Choisir un modèle {#pick-a-model}

Cliquez sur le nom du modèle sous la zone de message pour changer de modèle. Le changement s’applique à partir du message suivant, et la conversation garde tout ce qui a été dit jusque-là. Quand le sélecteur est ouvert, les touches <kbd>1</kbd> à <kbd>9</kbd> choisissent le modèle portant ce numéro.

Le sélecteur liste les modèles que vous avez activés pour chaque fournisseur dans **Settings** › **Providers** ; voir [Ajouter un fournisseur de modèles](../get-started/providers.md). Une nouvelle conversation démarre avec le **Default model** de **Settings** › **General**.

## Régler l’effort {#set-the-effort}

À côté du modèle se trouve le réglage d’effort, une échelle allant de **Faster** à **Smarter**. Plus d’effort laisse le modèle raisonner plus longtemps : meilleur sur les tâches difficiles, plus lent et plus coûteux. **Medium** est un bon point de départ.

Quand Coscribe connaît les niveaux propres au modèle, l’échelle les affiche, par exemple **Low**, **Medium**, **High**, **Extra high** et **Max**. Sinon, elle affiche l’échelle complète et le modèle utilise le niveau pris en charge le plus proche. Pour un modèle sans réglage d’effort, le contrôle est grisé.

Votre choix est conservé quand vous changez de modèle : le nouveau modèle utilise le niveau le plus proche dont il dispose.

## Surveiller le contexte {#watch-the-context}

Chaque modèle ne peut lire qu’une quantité limitée à la fois : sa fenêtre de contexte. Une fois la conversation commencée, un anneau à côté de la zone de message indique la part utilisée. Cliquez sur l’anneau pour voir ce qui occupe la place : les messages, le prompt système, les outils et compétences, et l’espace libre restant.

Quand la fenêtre est remplie aux quatre cinquièmes environ, Coscribe résume de lui-même la première partie de la conversation pour pouvoir continuer. Vous pouvez aussi taper `/compact` pour le faire tout de suite. Voir [Poursuivre une longue conversation](conversations.md#keep-a-long-conversation-going).

## Limiter les coûts {#keep-costs-down}

Vous payez le fournisseur pour ce que le modèle lit et écrit. Quelques habitudes aident :

- Utilisez un effort plus faible pour le travail courant.
- Démarrez une nouvelle conversation pour un nouveau travail, plutôt que de poursuivre une longue conversation.
- Désactivez **Prompt suggestions** et **Background agents** dans **Settings** › **General** si vous ne vous en servez pas ; tous deux ajoutent des appels au modèle.
- Pour un travail qui ne doit pas quitter votre PC, ou que vous faites souvent, un [modèle sur votre PC](../get-started/providers.md#run-a-model-on-your-pc) ne coûte rien à l’usage.
