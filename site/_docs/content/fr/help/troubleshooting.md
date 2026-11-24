---
title: Dépannage
description: Vérifiez avec /doctor ce dont Coscribe a besoin sur votre PC, corrigez les problèmes courants et signalez un problème.
---

## Lancer une vérification {#run-a-check}

Tapez `/doctor` dans n’importe quelle conversation. Coscribe vérifie ce dont il a besoin sur cet ordinateur et affiche une carte avec chaque résultat, les problèmes en premier, et comment corriger chacun. Une correction qui passe par un paramètre renvoie à sa page.

| Vérification | Ce qu’elle examine |
|---|---|
| **Model** | Si le modèle par défaut répond. Sinon : vérifiez la clé, l’adresse et le nom du modèle du fournisseur, ou le réseau et le [proxy](../reference/settings.md#general). |
| **Python for scripts** | S’il y a un Python pour les scripts. Sinon, téléchargez celui de Coscribe dans **Settings** › **Capabilities**. |
| **Node.js for scripts** | Si `node` et `npm` sont installés, pour les scripts Node.js. Installez-les depuis [nodejs.org](https://nodejs.org) si vous en avez besoin. |
| **Office conversion** | Si Microsoft Office ou LibreOffice est présent pour produire les aperçus de pages et convertir les documents. Si aucun des deux ne l’est, installez Office ou téléchargez LibreOffice dans **Settings** › **Capabilities**. |
| **Browser** | Si Microsoft Edge ou Google Chrome est installé, pour le panneau du navigateur et les images de pages. |
| **Script isolation** | Si les scripts peuvent s’exécuter dans leur conteneur isolé. Tant que l’autotest n’a pas réussi, les scripts sont désactivés ; relancez-le dans les paramètres de l’espace de travail. |
| **Command sandbox** | Si les commandes s’exécutent dans le bac à sable. S’il n’est pas configuré, chaque commande s’exécute en votre nom, après votre approbation. |

## Problèmes courants {#common-problems}

### Une réponse échoue ou n’arrive jamais {#a-reply-fails-or-never-comes}

Lancez `/doctor` et regardez **Model**. Une clé expirée, un nom de modèle erroné ou un réseau qui exige un proxy en sont les causes habituelles. Certains réseaux d’entreprise bloquent les services d’IA ; adressez-vous à votre service informatique, ou réglez le proxy dans **Settings** › **General** › **Proxy**.

### Coscribe ne peut pas ouvrir un fichier ou un dossier {#coscribe-cant-open-a-file-or-folder}

Coscribe ne travaille que dans son espace de travail et les dossiers que vous avez autorisés. Quand il demande un autre dossier, autorisez-le, ou ajoutez le dossier à l’espace de travail. Voir [Donner accès à un autre dossier](../use/approvals.md#give-access-to-another-folder).

Si vous modifiez le même fichier Word, Excel ou PowerPoint, enregistrez vos modifications avant de faire votre demande. Coscribe remarque qu’un fichier a changé depuis sa dernière lecture, le relit et apporte sa modification à votre version, mais il ne voit que ce que vous avez enregistré.

### Les scripts ne s’exécutent pas {#scripts-dont-run}

Vérifiez que **Run scripts** est activé dans **Settings** › **Capabilities**, puis lancez `/doctor` et regardez **Python for scripts** et **Script isolation**.

### Un connecteur ne fonctionne plus {#a-connector-stops-working}

Ouvrez-le dans **Settings** › **Connectors**. S’il indique qu’il n’est pas connecté, cliquez sur **Retry**, ou sur **Sign in** si sa connexion a expiré.

### Une tâche planifiée ne s’est pas exécutée {#a-scheduled-task-didnt-run}

Les tâches ne s’exécutent que lorsque Coscribe est en cours d’exécution, dans la fenêtre ou dans la zone de notification. Vérifiez que **Keep running in the background** est activé dans **Settings** › **General** et que la tâche n’est pas en pause. Une exécution prévue pendant que Coscribe était fermé s’exécute une fois à son redémarrage. Voir [Tâches planifiées](../workflows/scheduled-tasks.md).

## Signaler un problème {#report-a-problem}

Signalez-le sur [GitHub](https://github.com/OICWS/coscribe/issues/new). Indiquez ce que vous avez demandé, ce qui s’est passé à la place et ce qu’affiche `/doctor`.

Pour montrer comment un tour a mal tourné sans partager vos mots, faites un clic droit sur la conversation dans la barre latérale et choisissez **Export a failed turn…**. Le fichier décrit le déroulement du tour : le modèle, ses appels d’outils et ses échecs, les jetons et la durée, et le début de chaque erreur d’outil. Il ne contient aucun mot de la conversation, et rien n’est envoyé : vous enregistrez le fichier et décidez à qui le donner.

Le journal du serveur est `%APPDATA%\Coscribe\logs\coscribe-server.log`.
