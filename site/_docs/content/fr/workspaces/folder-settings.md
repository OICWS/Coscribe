---
title: Notes et règles propres à un dossier
description: Laissez un dossier indiquer à coscribe ce qu’il contient, quelles compétences et quels connecteurs utiliser, et ce qui peut s’exécuter sans demander.
---

Un dossier peut transporter des instructions pour coscribe dans un dossier `.coscribe` qu’il contient. coscribe les lit pour toute conversation qui utilise le dossier, une fois que vous les avez acceptées.

## Ce qu’un dossier peut contenir {#what-a-folder-can-hold}

| Fichier | Rôle |
|---|---|
| `.coscribe/memory.md` | Des notes que coscribe lit au début de chaque conversation dans ce dossier : à quoi sert le dossier, ses conventions, ses noms. |
| `.coscribe/skills/<name>/SKILL.md` | Des [compétences](../customize/skills.md) qui ne s’appliquent que dans ce dossier. |
| `.coscribe/settings.json` | Des règles d’autorisation (`allow`, `ask`, `deny`) et des variables d’environnement pour les scripts. |
| `.coscribe/mcp.json` | Les [connecteurs](../customize/connectors.md) qu’utilise ce dossier. |

coscribe lui-même n’écrit jamais `memory.md`, `settings.json` ni `mcp.json` ; vous seul les modifiez. Les pièces jointes que vous envoyez sont conservées dans `.coscribe/uploads/`.

## Accepter les paramètres d’un dossier {#accept-a-folders-settings}

Les paramètres d’un dossier peuvent venir de toute personne capable d’y écrire ; coscribe ne les suit donc pas tant que vous n’êtes pas d’accord. Le panneau **Task details** affiche **What Coscribe knows about this folder**, qui liste les compétences, connecteurs et règles apportés par le dossier, regroupés en **Runs without asking**, **Always asks** et **Never runs**, ainsi que les éventuelles variables pour les scripts. Cliquez sur **Use them** pour accepter.

Si l’un de ces fichiers change en dehors de coscribe, il redemande.

## Règles d’autorisation {#permission-rules}

`.coscribe/settings.json` a le même format que le fichier de paramètres de Claude Code :

```json
{
  "permissions": {
    "allow": ["write_file(reports/*)"],
    "ask": ["run_background_command"],
    "deny": ["delete_file"]
  },
  "env": {
    "REPORT_REGION": "East"
  }
}
```

Une règle est un nom d’outil de coscribe, un motif de noms avec `*`, ou l’un des deux suivi entre parenthèses d’un motif de son argument principal, comme `write_file(docs/*)`. Les règles ne décident que des actions qui, sinon, attendraient votre approbation. **deny** l’emporte sur **ask**, et **ask** sur **allow**.

Certaines limites s’appliquent toujours :

- Une règle n’autorise jamais une action qui quitte votre ordinateur, comme l’envoi d’un message via un connecteur ; celles-ci demandent toujours.
- Un `*` seul n’autorise rien.
- Une règle `ask` demande même en mode **Auto**.

## Variables pour les scripts {#variables-for-scripts}

Les valeurs `env` de `settings.json` sont transmises aux scripts et aux commandes du dossier. Un dossier ne peut pas définir de variables qui changent les programmes exécutés ou la destination du trafic, comme `PATH`, les paramètres de proxy ou `PYTHONPATH`.
