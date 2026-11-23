---
title: Le navigateur intégré
description: Laissez Coscribe utiliser des sites web dans un navigateur que vous pouvez observer, reprendre en main et contrôler site par site.
---

L’application de bureau a son propre navigateur, affiché dans le panneau **Browser**. Coscribe l’utilise sous vos yeux : il ouvre des pages, remplit des formulaires entiers, envoie et télécharge des fichiers, enregistre des tableaux (sur plusieurs pages) en fichiers CSV et des pages en PDF. Les connexions sont conservées d’une session à l’autre : vous ne vous connectez à un site qu’une fois.

> [!NOTE]
> Le navigateur fait partie de l’application de bureau. Si vous utilisez Coscribe dans votre propre navigateur web, il n’y a pas de panneau Browser.

## Autoriser un site {#allow-a-site}

La première fois que Coscribe veut utiliser un site, le panneau Browser vous demande :

- **Allow for this chat** l’autorise à utiliser le site dans cette conversation.
- **Always allow** ajoute le site à l’espace de travail, pour qu’il soit utilisé sans demander à l’avenir.
- **Don't allow** refuse.

Chaque espace de travail conserve un niveau par site sous **Edit workspace › Sites** : **Use without asking**, **Ask each time** ou **Not in the browser**. L’entrée la plus précise l’emporte : `admin.example.com` peut rester exclu tandis que `example.com` est autorisé.

## Reprendre la main {#take-over}

Cliquez sur **Take over** pour utiliser la page vous-même ; Coscribe attend. Cliquez sur **Allow AI** pour lui rendre la main.

Quand un site demande un mot de passe, un code à usage unique ou un captcha, Coscribe s’arrête et vous demande de vous en charger. Il ne tape jamais un mot de passe ou un code que vous ne lui avez pas donné.

## Désigner un élément {#point-at-something}

- **Select element** vous permet de cliquer sur une partie de la page pour l’envoyer dans la conversation.
- **Annotate** prend une image de la page que vous pouvez annoter et envoyer avec **Add to chat**.
