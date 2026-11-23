---
title: Compétences et plugins
description: Apprenez une fois à Coscribe une façon de travailler, ajoutez des compétences créées par d’autres, et activez-les ou désactivez-les.
---

Une compétence (skill) est un ensemble d’instructions pour un type de travail, par exemple la façon dont votre équipe rédige un rapport hebdomadaire. Quand un travail correspond à la description d’une compétence, Coscribe la suit. Coscribe est livré avec quelques compétences intégrées, et vous pouvez ajouter les vôtres.

## Utiliser une compétence {#use-a-skill}

Vous n’avez rien à faire : Coscribe choisit une compétence quand elle convient. Pour en utiliser une délibérément, tapez <kbd>/</kbd> dans la zone de message et choisissez-la dans la liste, ou tapez son nom après la barre oblique, suivi de votre demande.

## Enregistrer un travail comme compétence {#save-a-job-as-a-skill}

Après avoir fait un travail dans une conversation, vous pouvez garder la façon dont il a été fait :

- Tapez `/create-skill` suivi d’un nom.
- Ou choisissez **Save as skill** quand Coscribe propose **Save this job?** après un travail en plusieurs étapes.

Vous pouvez aussi partir de **Settings** › **Skills** › **Add** › **Create with Coscribe**, qui ouvre une conversation pour décrire la compétence.

## Ajouter des compétences créées par d’autres {#add-skills-others-made}

Dans **Settings** › **Skills** :

- **Discover** liste des compétences open source issues de [github.com/anthropics/skills](https://github.com/anthropics/skills) et de [github.com/anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins). La plupart sont fournies sous forme de plugin : un ensemble de compétences. Ouvrez-en un pour voir ses compétences, les connecteurs qu’il utilise et sa licence ; **Add** télécharge toutes ses compétences.
- **Add** › **Upload a skill** accepte un fichier de compétence que l’on vous a donné : un `SKILL.md`, ou un fichier `.zip`, `.skill` ou `.plugin`.

> [!WARNING]
> Une compétence est un ensemble d’instructions que Coscribe suit. N’ajoutez que des compétences de personnes de confiance, et lisez-en une avant de l’utiliser : ouvrez-la dans **Yours** pour voir ses fichiers.

## Activer ou désactiver des compétences {#turn-skills-on-or-off}

**Yours** liste vos compétences. Ouvrez-en une pour lire ses fichiers, et utilisez son interrupteur pour la désactiver sans la supprimer. Le menu à côté d’une compétence la supprime. Supprimer une compétence venue d’un plugin supprime toutes les compétences de ce plugin.

## Compétences pour un dossier {#skills-for-one-folder}

Un dossier peut apporter ses propres compétences dans `.coscribe/skills/`. Elles ne s’appliquent que dans les conversations qui utilisent ce dossier, une fois que vous avez accepté ses paramètres. Voir [Notes et règles propres à un dossier](../workspaces/folder-settings.md).

## Écrire une compétence à la main {#write-a-skill-by-hand}

Une compétence est un dossier contenant un fichier `SKILL.md`. Le fichier commence par un `name` et une `description`, puis viennent les instructions en Markdown :

```markdown
---
name: Weekly report
description: Write the weekly sales report from the order export. Use when asked for the weekly report.
---

1. Read the latest export in Reports/Exports.
2. ...
```

La description détermine quand Coscribe utilise la compétence : indiquez donc à quoi elle sert et quand l’utiliser. C’est le même format que les compétences de Claude Code.
