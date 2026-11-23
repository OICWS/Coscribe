---
title: Classeurs Excel
description: Faites lire, nettoyer, totaliser et rapprocher des feuilles de calcul par coscribe, et créez des classeurs avec formules et graphiques.
---

coscribe lit les fichiers `.xlsx` feuille par feuille et écrit de vrais classeurs : cellules, styles, formules et graphiques Excel natifs.

## Que demander {#what-to-ask-for}

- **Nettoyer et totaliser** : « Supprime les lignes sans adresse de livraison et totalise les montants par fournisseur. »
- **Rapprocher** : « Rapproche le relevé bancaire de notre grand livre et liste ce qui ne concorde pas. »
- **Construire un modèle** : « Fais un budget sur 12 mois avec une feuille de synthèse qui additionne les services. »
- **Faire un graphique** : « Ajoute un histogramme du chiffre d’affaires par région à côté du tableau. »

Nommez les fichiers, et les feuilles si un classeur en contient plusieurs, et dites ce que doit être le résultat : un nouveau fichier, une nouvelle feuille ou une modification de l’existant.

## Les formules restent des formules {#formulas-stay-formulas}

Quand une valeur dépend d’autres cellules, coscribe l’écrit sous forme de formule Excel, pour que le classeur continue de fonctionner quand vous changez un nombre. Il calcule aussi les formules et enregistre leurs résultats dans le fichier, pour que les valeurs s’affichent même dans les programmes qui ne recalculent pas à l’ouverture.

## Travaux volumineux ou inhabituels {#large-or-unusual-jobs}

Pour un travail que les outils intégrés ne couvrent pas, coscribe peut écrire un script Python (avec `pandas` et `openpyxl`, par exemple) et l’exécuter, avec votre approbation. Voir [Approbations et modes d’autorisation](../use/approvals.md).

> [!TIP]
> Vous voulez que coscribe suive les conventions de votre équipe, comme des couleurs pour les entrées et les sorties ou un format de nombre ? Mettez-les dans vos [instructions](../customize/instructions.md) ou dans une [compétence](../customize/skills.md).
