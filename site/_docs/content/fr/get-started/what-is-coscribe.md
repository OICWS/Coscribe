---
title: Qu’est-ce que Coscribe
description: Un assistant de bureautique qui fonctionne sur votre PC et crée des fichiers Word, Excel et PowerPoint modifiables.
---

Coscribe est un assistant de bureautique à IA pour Windows. Dites en une phrase ce dont vous avez besoin : il lit vos feuilles de calcul et vos documents et crée le fichier final, qu’il s’agisse d’un contrat avec suivi des modifications et commentaires, d’une présentation de rapport avec graphiques ou d’un classeur Excel rapproché.

Il est open source (licence MIT) et gratuit. Vous ne payez que le service de modèles que vous choisissez.

## Ce qu’il sait faire {#what-it-can-do}

- **Excel** : lire, nettoyer, synthétiser et rapprocher des données ; écrire des formules et des graphiques.
- **Word** : rédiger et réviser des documents, en marquant les changements avec le suivi des modifications et des commentaires pour que d’autres puissent les relire.
- **PowerPoint** : transformer des données et des documents en présentation, avec le modèle et les couleurs de votre entreprise si vous en avez.
- **PDF** : rechercher, extraire et organiser le contenu.
- **Le web** : ouvrir des sites dans un navigateur intégré, remplir des formulaires et enregistrer des tableaux.
- **Workflows** : enregistrer ce qu’une conversation a fait sous forme d’étapes fixes, puis le relancer en un clic ou selon un planning.

## Ce qui le distingue des autres outils d’IA {#how-it-differs-from-other-ai-tools}

**Vos fichiers restent sur votre PC.** Coscribe n’a pas de service cloud à lui. Seul ce que le modèle doit lire est envoyé au fournisseur de modèles que vous avez choisi ; avec un modèle qui tourne sur votre propre ordinateur via Ollama, rien ne quitte la machine.

**Vous choisissez le modèle.** Claude, GPT et Gemini sont intégrés. DeepSeek, Kimi, GLM, Qwen, Doubao et tout autre service doté d’une API compatible OpenAI fonctionnent dès que vous saisissez son adresse et votre clé API. Voir [Ajouter un fournisseur de modèles](providers.md).

**Il demande avant de modifier.** Quatre modes d’autorisation vont de « demande-moi avant chaque étape » à « laisse un modèle relecteur approuver le travail courant à ma place ». Quel que soit le mode, il n’écrit que dans les dossiers que vous avez autorisés. Voir [Votre première conversation](first-conversation.md#permission-modes).

**Il vous remet des fichiers finis, pas des brouillons.** Après avoir écrit un fichier, Coscribe en fait le rendu et regarde le résultat pour vérifier la mise en page et le contenu, plutôt que de vous remettre un bloc de texte.

## Configuration requise {#system-requirements}

- Windows 10 ou Windows 11.
- Une clé API d’un service de modèles, ou Ollama ou LM Studio en cours d’exécution sur votre PC.

> [!NOTE]
> Coscribe n’est disponible que pour Windows. Il n’existe pas encore de version Mac ou Linux.
