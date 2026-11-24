---
title: Workflows
description: Enregistrez un travail sous forme d’étapes fixes, lancez-le selon un planning ou sur un événement, et choisissez ce que l’IA peut décider quand une étape ne fonctionne plus.
---

Un workflow est une tâche composée d’étapes fixes. Contrairement à une tâche planifiée qui suit des instructions écrites, un workflow exécute les mêmes étapes à chaque fois et les vérifie pendant l’exécution : vous voyez donc ce qu’il fera avant qu’il le fasse. Planning, autorisations et rapports d’exécution fonctionnent comme pour les [tâches planifiées](scheduled-tasks.md).

## Créer un workflow {#make-a-workflow}

Le plus simple est de faire le travail une fois dans un chat, puis d’en faire un workflow :

- Choisissez **Save as workflow** quand Coscribe propose **Save this job?**, ou dans le panneau **Task details**.
- Ou tapez `/saveworkflow` dans la zone de message, suivi d’un nom si vous le souhaitez.

Coscribe prépare les étapes à partir de la conversation. Relisez-les, puis enregistrez.

Vous pouvez aussi partir de zéro : **Scheduled** › **New task** › **Build a workflow**. Donnez-lui un nom et un planning, enregistrez, puis ajoutez les étapes sur sa page.

## La page du workflow {#the-workflow-page}

La page comporte quatre onglets :

- **Overview** explique en mots simples ce que fait le workflow : quand il s’exécute, sur quoi il travaille, où il s’arrête pour vous attendre et ce qu’il peut toucher. **Show the flowchart** dessine les étapes.
- **Steps** liste les étapes ; vous y ajoutez, modifiez et réordonnez les étapes. La vue peut aussi être un **Flowchart**.
- **Runs** liste les exécutions passées.
- **Settings** contient le planning, l’espace de travail et les autorisations.

**Run now** est grisé tant que le workflow n’a pas d’étapes. Si le workflow prend des entrées, comme un fichier, il les demande d’abord.

## Types d’étapes {#kinds-of-steps}

**Add a step** propose ces types :

| Étape | Ce qu’elle fait |
|---|---|
| **Tool** | Utilise un des outils de Coscribe, sans modèle. |
| **Script** | Exécute un script Python fixe que vous avez relu. |
| **Model** | Un appel au modèle qui doit renvoyer des champs définis. |
| **Agent** | Travaille vers un objectif avec des outils, dans les limites que vous fixez : les outils qu’il peut appeler, les dossiers qu’il peut modifier et les sites qu’il peut ouvrir. |
| **Check** | Arrête l’exécution si des valeurs ne sont pas vérifiées. |
| **Approval** | Se met en pause jusqu’à votre approbation. |
| **Ask you** | Se met en pause jusqu’à ce que vous remplissiez des valeurs utilisées par les étapes suivantes. |
| **Wait** | Se met en pause un moment, jusqu’à une heure donnée ou jusqu’à l’apparition d’un fichier. |
| **Remember** | Garde une valeur pour l’exécution suivante, comme ce qui a déjà été traité. |
| **Run a task** | Exécute une autre de vos tâches comme une étape et utilise ses résultats. |
| **If / otherwise** | Exécute des étapes différentes selon une valeur. |
| **Choose a path** | Plusieurs chemins, choisis selon la valeur d’un élément. |
| **At the same time** | Exécute 2 à 6 voies d’étapes en même temps, puis continue. |
| **For each** | Répète des étapes pour chaque élément d’une liste. |

Pour chaque étape, vous pouvez choisir ce qui se passe si elle échoue : **Stop the run**, **Skip it and go on** ou **Run other steps instead**. Une étape peut aussi réessayer un nombre de fois défini.

## Quand une étape ne fonctionne plus {#autonomy}

Les sites web changent et les fichiers varient d’une exécution à l’autre. Le réglage **If a step stops working** détermine ce que l’IA peut décider dans ce cas :

| Niveau | Ce qui se passe |
|---|---|
| **Fixed** | Seules les étapes enregistrées s’exécutent. Si l’une échoue, l’exécution s’arrête et vous prévient. |
| **Self-healing** | Si un site web a changé, l’IA effectue cette étape sur la page telle qu’elle est maintenant. |
| **Proactive** | Les étapes d’IA décident comment faire leur part. Si une étape échoue, l’IA peut ajouter quelques étapes ; celles qui modifient quelque chose vous attendent. |
| **Autonomous** | L’IA peut faire toute la tâche à sa façon. |

Quand une exécution a contourné un changement, Coscribe peut proposer des étapes mises à jour à relire, pour que l’exécution suivante n’ait pas à le faire.

## Lancer un workflow sur un événement {#start-on-an-event}

En plus des plannings communs à toutes les tâches, la **Frequency** d’un workflow peut être :

- **Every few minutes**.
- **When a file arrives in a folder** : choisissez le **Folder to watch** et, si vous le souhaitez, un **File name pattern**. Chaque nouveau fichier lance une exécution, avec le fichier comme entrée de fichier du workflow. L’option nécessite un workflow qui prend un fichier.
- **When something new shows up in a connector** : choisissez un connecteur et ce qu’il faut lui demander. Coscribe l’interroge toutes les quelques minutes, et chaque nouvel élément lance une exécution. La première vérification considère comme déjà vu ce qui existe déjà.
- **When a program sends it an event** : un autre programme sur le même ordinateur envoie une requête, avec une clé, à une adresse que Coscribe affiche. **Wait for a sample** garde l’événement suivant pour que vous choisissiez lesquels de ses champs remplissent les entrées. L’adresse n’accepte que les requêtes de votre propre ordinateur.

Un fichier arrivé pendant que Coscribe était fermé lance une exécution au redémarrage de Coscribe.
