---
title: Approbations et modes d’autorisation
description: Choisissez ce que Coscribe peut faire seul, et répondez aux cartes qu’il affiche quand il a besoin de vous.
---

Coscribe ne fait rien hors de sa portée sans votre accord. La fréquence de ses questions dépend du mode d’autorisation de la conversation ; ce qu’il peut atteindre dépend de l’[espace de travail](../workspaces/workspaces.md).

## Les quatre modes {#the-four-modes}

Choisissez un mode avec le bouton de mode sous la zone de message. Le mode par défaut des nouvelles conversations se règle dans **Settings › General › Default mode**.

| Mode | Ce qu’il fait |
|---|---|
| **Manual** | Demande avant chaque modification, script ou action extérieure. |
| **Accept Edits** | Modifie les fichiers de vos dossiers sans demander ; demande toujours avant d’exécuter du code ou une action extérieure. |
| **Plan** | Étudie la tâche et rédige un plan que vous approuvez avant toute modification. Voir [Plans et listes de tâches](plans.md). |
| **Auto** | Un modèle relecteur approuve les actions courantes et bloque les actions risquées au lieu de vous demander. |

Si vous changez de mode pendant une réponse, le nouveau mode s’applique à la fin de la réponse.

## Approuver une action {#approve-an-action}

Quand Coscribe a besoin de votre approbation, une carte dans la conversation nomme l’action, par exemple « Run a command », et montre ce qu’elle fera : le fichier qu’elle écrira, le script ou la commande. Lisez-la, puis choisissez :

- **Approve** autorise cette action-là.
- **Allow for this task** (affiché pour les commandes et modifications du module de code) autorise le même type d’action pour le reste de la tâche sans redemander.
- **Deny** la refuse. Pour expliquer pourquoi, tapez plutôt votre raison dans la zone de message ; Coscribe la lit et s’adapte.

Si la carte est sortie de l’écran, un avis au-dessus de la zone de message indique que quelque chose attend ; **Show** vous y ramène.

> [!IMPORTANT]
> La carte d’un script indique comment il s’exécutera. Normalement, un script s’exécute isolé : il ne peut utiliser que les dossiers de la conversation, ne peut pas y supprimer ni renommer de fichiers, et n’accède à Internet que si le paramètre **Sites** de l’espace de travail est **Any site**. Un badge **Not isolated** signifie que le script s’exécutera sans cette isolation et pourra atteindre tous les fichiers auxquels vous avez accès ; survolez le badge pour savoir pourquoi, et lisez le script avant d’approuver.

## Donner accès à un autre dossier {#give-access-to-another-folder}

Quand Coscribe a besoin d’un dossier hors de l’espace de travail et des dossiers que vous avez autorisés, il le demande sur une carte. Choisissez l’accès (**Read only**, **Read and write** ou **Read, write and delete**), puis :

- **Allow** ajoute définitivement le dossier à vos dossiers autorisés.
- **Only this chat** l’autorise pour cette conversation uniquement.
- **Save in my workspace instead** (quand il voulait écrire) garde le fichier dans l’espace de travail.
- **Don't allow** refuse.

Coscribe ne propose jamais un lecteur entier ni votre dossier personnel.

## Installer un paquet pour un script {#install-a-package-for-a-script}

Un script peut avoir besoin d’une bibliothèque Python ou Node.js que Coscribe n’a pas encore. La carte **Install a Python package** (ou Node.js) la nomme et explique pourquoi. **Install** l’installe dans l’environnement propre à Coscribe, que le reste de votre ordinateur n’utilise pas ; **Not now** refuse pour cette conversation. Si l’installation échoue, **Details** affiche la sortie de l’installateur.

## Répondre à une question {#answer-a-question}

Parfois, Coscribe vous demande de choisir, par exemple entre deux mises en page. Choisissez une option sur la carte ou tapez votre propre réponse dans la zone de message.
