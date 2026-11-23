---
title: Connecteurs
description: Connectez coscribe aux services que vous utilisez, comme votre messagerie, votre agenda ou votre outil de suivi de projet, et choisissez ce qu’il peut y faire.
---

Un connecteur permet à coscribe d’utiliser un autre service : lire vos e-mails, ajouter un événement à un agenda, consulter un ticket. Les connecteurs utilisent le Model Context Protocol (MCP) : n’importe quel serveur MCP fonctionne, pas seulement ceux que coscribe liste.

## Ajouter un connecteur {#add-a-connector}

Ouvrez **Settings** › **Connectors** › **Discover**, choisissez le service et cliquez sur **Connect**.

- La plupart des services hébergés vous demandent de vous connecter. La connexion s’ouvre sur la page du service lui-même, dans votre navigateur, et vous ne vous connectez qu’une fois. coscribe ne voit jamais votre mot de passe.
- Un service marqué **Needs setup** exige d’abord une application enregistrée auprès de lui. coscribe vous guide, une seule fois. Si quelqu’un l’a déjà configuré pour votre équipe, **Copy a message for your admin** lui demande le fichier de configuration.

coscribe peut aussi proposer un connecteur dans une conversation, quand votre demande nécessite un service que vous n’avez pas connecté. Cliquez sur **Connect** sur la carte, et coscribe continue dès que la connexion est établie. **Not now** laisse les choses en l’état ; vous pouvez le connecter à tout moment dans **Settings** › **Connectors**.

## Ajouter un connecteur personnalisé {#add-a-custom-connector}

Pour un serveur MCP qui n’est pas listé, choisissez **Add** › **Add custom connector**, donnez-lui un nom, puis :

- Saisissez l’**MCP server URL** d’un serveur hébergé, avec les en-têtes nécessaires. Pour placer une clé dans un en-tête sans l’écrire en clair, utilisez **Insert a secret** ; l’en-tête devient alors `{{secret:NAME}}` et la valeur provient de [Secrets](../reference/settings.md#secrets).
- Ou choisissez **Run a local command instead** et saisissez la commande, comme `npx`, ses arguments et les variables d’environnement nécessaires. Elle s’exécute comme un programme sur cet ordinateur, avec vos droits.

> [!WARNING]
> Une commande locale s’exécute avec tout ce que votre compte Windows peut faire. N’ajoutez que des serveurs de confiance.

## Choisir ce qu’il peut faire {#choose-what-it-may-do}

Ouvrez un connecteur dans **Yours** pour voir ses outils, répartis entre **Read-only tools** et **Write/delete tools**. Pour chaque outil, choisissez :

| Choix | Ce qui se passe |
|---|---|
| **Always allow** | coscribe l’utilise sans demander. |
| **Needs approval** | coscribe vous demande à chaque fois. Voir [Approbations et modes d’autorisation](../use/approvals.md). |
| **Blocked** | coscribe ne peut pas l’utiliser. |

La page du connecteur indique aussi s’il est connecté. Si ce n’est pas le cas, **Retry** relance la connexion, et **Sign in** ouvre la page de connexion du service.

## Connecteurs pour un dossier {#connectors-for-one-folder}

Un dossier peut apporter ses propres connecteurs dans `.coscribe/mcp.json`. Ils ne s’appliquent que dans les conversations qui utilisent ce dossier, une fois que vous avez accepté ses paramètres. Voir [Notes et règles propres à un dossier](../workspaces/folder-settings.md).

## Utiliser un connecteur dans un workflow {#use-a-connector-in-a-workflow}

Les outils d’un connecteur peuvent être des étapes d’un [workflow](../workflows/workflows.md), et un workflow peut démarrer quand quelque chose de nouveau apparaît dans un connecteur. Voir [Lancer un workflow sur un événement](../workflows/workflows.md#start-on-an-event).
