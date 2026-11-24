---
title: Tâches planifiées
description: Faites exécuter un travail par Coscribe selon un planning, comme un point du matin, et lisez le rapport de chaque exécution.
---

Une tâche planifiée est un travail que Coscribe fait sans vous : à une heure donnée, toutes les heures ou quand vous la lancez. Chaque exécution est une conversation à part entière et se termine par un rapport.

Il en existe deux sortes. Une **tâche planifiée** suit des instructions écrites : le modèle décide donc de chaque étape à chaque fois. Un **workflow** exécute des étapes fixes que vous avez enregistrées, vérifiées pendant l’exécution ; voir [Workflows](workflows.md). Cette page décrit ce que les deux ont en commun.

## Créer une tâche {#create-a-task}

Ouvrez **Scheduled** dans la navigation, puis **New task** :

- **Create with Coscribe** ouvre un chat pour que vous décriviez le travail, ou que vous le parcouriez une fois. Coscribe prépare ensuite la tâche dans une carte ; **Review & save** l’ouvre pour que vous puissiez tout modifier avant d’enregistrer.
- **Set up manually** ouvre le formulaire, où vous écrivez vous-même le nom, les instructions et le planning.
- **Build a workflow** crée un workflow vide. Voir [Workflows](workflows.md).

Après un travail fait dans un chat, Coscribe peut aussi proposer **Save this job?**. **Save as workflow** le transforme en étapes fixes que vous pouvez relancer ou planifier ; **Save as skill** le garde comme instructions pour la prochaine fois (voir [Compétences](../customize/skills.md)).

## Choisir quand elle s’exécute {#choose-when-it-runs}

**Frequency** peut être **Manual** (seulement quand vous la lancez), **Hourly**, **Daily**, **Weekdays**, **Weekly** ou **Monthly**. Les exécutions quotidiennes, en semaine et hebdomadaires prennent une heure ; les hebdomadaires prennent aussi un jour. Un workflow peut aussi s’exécuter toutes les quelques minutes, ou quand quelque chose se produit ; voir [Lancer un workflow sur un événement](workflows.md#start-on-an-event).

Une tâche a aussi un **Workspace**, qui détermine les dossiers et sites que ses exécutions peuvent utiliser (voir [Espaces de travail et dossiers](../workspaces/workspaces.md)), et un **Model**. **Default model** utilise le modèle défini dans vos paramètres.

## Choisir ce qu’elle peut faire sans vous {#choose-what-it-may-do-without-you}

Personne ne surveille une exécution ; une tâche définit donc ses propres **Permissions** :

| Réglage | Ce qui se passe |
|---|---|
| **Ask before every action** | L’exécution se met en pause et attend votre approbation avant toute action qui en a besoin. |
| **Automatically approve** | L’exécution crée et modifie des fichiers seule, mais se met en pause avant d’exécuter du code ou d’utiliser des connecteurs. |
| **Never ask** | L’exécution ne se met jamais en pause pour une approbation, y compris pour exécuter du code ou utiliser des connecteurs. Vos règles de blocage s’appliquent toujours. |

**Most steps** met fin à une exécution après ce nombre d’étapes, pour qu’une exécution qui tourne mal ne puisse pas durer longtemps.

> [!WARNING]
> Avec **Never ask**, une exécution peut lancer du code et utiliser vos connecteurs sans demander. Ne l’utilisez que pour une tâche dont vous faites confiance aux instructions.

## Garder l’application ouverte {#keep-the-app-running}

Fermer la fenêtre de Coscribe le laisse tourner dans la zone de notification, et les tâches continuent de s’exécuter. Pour quitter, choisissez **Quit** dans l’icône de la zone de notification. Si vous désactivez **Keep running in the background** dans **Settings** › **General**, fermer la fenêtre quitte Coscribe, et les tâches s’arrêtent avec lui.

Si une exécution était prévue pendant que Coscribe était fermé, elle s’exécute une fois au redémarrage de Coscribe.

## Suivre les exécutions {#follow-the-runs}

La page d’une tâche indique sa prochaine exécution, ses exécutions récentes et leur état : **Running**, **Completed**, **Failed**, **Needs approval**, **Waiting** ou **Stopped**. Ouvrez une exécution pour voir sa conversation et son rapport. Une exécution qui a besoin d’approbation vous y attend.

- **Run now** lance immédiatement une exécution, pour essayer la tâche.
- L’interrupteur à côté de l’état met la tâche en pause ou la reprend.
- Le crayon renomme la tâche ou change le moment où elle s’exécute.

**Notifications** dans **Settings** › **General** détermine si Coscribe vous prévient à la fin de chaque exécution, ou seulement en cas de problème : une exécution qui a échoué ou qui vous attend. Cliquer sur une notification ouvre l’exécution.

## Mémoire entre les exécutions {#remember-between-runs}

Activez **Remember between runs** sur la page d’une tâche planifiée, et chaque exécution écrit des notes pour la suivante : son avancement, où elle s’est arrêtée et ce qui a changé. Si l’option est désactivée, chaque exécution démarre sans notes.
