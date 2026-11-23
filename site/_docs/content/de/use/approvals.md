---
title: Genehmigungen und Berechtigungsmodi
description: Wählen Sie, wie viel coscribe selbst tun darf, und beantworten Sie die Karten, die es zeigt, wenn es Sie braucht.
---

coscribe tut nichts außerhalb seiner Reichweite ohne Ihr Einverständnis. Wie oft es fragt, hängt vom Berechtigungsmodus der Unterhaltung ab; was es überhaupt erreichen kann, hängt vom [Arbeitsbereich](../workspaces/workspaces.md) ab.

## Die vier Modi {#the-four-modes}

Wählen Sie einen Modus mit der Modus-Schaltfläche unter dem Nachrichtenfeld. Der Standard für neue Unterhaltungen wird unter **Settings › General › Default mode** festgelegt.

| Modus | Was er tut |
|---|---|
| **Manual** | Fragt vor jeder Änderung, jedem Skript und jeder Aktion nach außen. |
| **Accept Edits** | Bearbeitet Dateien in Ihren Ordnern ohne Nachfrage; fragt weiterhin, bevor Code ausgeführt wird oder eine Aktion nach außen geht. |
| **Plan** | Recherchiert und schreibt einen Plan, den Sie vor jeder Änderung genehmigen. Siehe [Pläne und Aufgabenlisten](plans.md). |
| **Auto** | Ein Prüfmodell genehmigt Routineaktionen und blockiert riskante, statt Sie zu fragen. |

Wechseln Sie den Modus, während eine Antwort läuft, gilt der neue Modus ab dem Ende der Antwort.

## Eine Aktion genehmigen {#approve-an-action}

Braucht coscribe Ihre Genehmigung, nennt eine Karte in der Unterhaltung die Aktion, etwa „Run a command“, und zeigt, was sie tun wird: die Datei, die sie schreibt, das Skript oder den Befehl. Lesen Sie sie und wählen Sie dann:

- **Approve** lässt diese eine Aktion zu.
- **Allow for this task** (angezeigt für Befehle und Änderungen des Code-Moduls) lässt dieselbe Art von Aktion für den Rest der Aufgabe ohne erneute Nachfrage zu.
- **Deny** lehnt sie ab. Um den Grund zu nennen, tippen Sie ihn stattdessen ins Nachrichtenfeld; coscribe liest ihn und passt sich an.

Ist die Karte aus dem Bild gescrollt, zeigt ein Hinweis über dem Nachrichtenfeld, dass etwas wartet; **Show** bringt Sie dorthin zurück.

> [!IMPORTANT]
> Die Karte eines Skripts sagt, wie es ausgeführt wird. Normalerweise läuft ein Skript isoliert: Es kann nur die Ordner der Unterhaltung nutzen, dort keine Dateien löschen oder umbenennen und erreicht das Internet nur, wenn die Einstellung **Sites** des Arbeitsbereichs **Any site** ist. Ein Abzeichen **Not isolated** bedeutet, dass das Skript ohne diese Isolation läuft und jede Datei erreichen kann, die Sie erreichen; fahren Sie mit der Maus über das Abzeichen, um den Grund zu sehen, und lesen Sie das Skript, bevor Sie genehmigen.

## Zugriff auf einen anderen Ordner gewähren {#give-access-to-another-folder}

Braucht coscribe einen Ordner außerhalb des Arbeitsbereichs und der erlaubten Ordner, fragt es auf einer Karte. Wählen Sie den Zugriff (**Read only**, **Read and write** oder **Read, write and delete**) und dann:

- **Allow** fügt den Ordner dauerhaft zu Ihren erlaubten Ordnern hinzu.
- **Only this chat** erlaubt ihn nur für diese Unterhaltung.
- **Save in my workspace instead** (wenn es schreiben wollte) behält die Datei im Arbeitsbereich.
- **Don't allow** lehnt ab.

coscribe bietet nie ein ganzes Laufwerk oder Ihren Benutzerordner an.

## Ein Paket für ein Skript installieren {#install-a-package-for-a-script}

Ein Skript braucht vielleicht eine Python- oder Node.js-Bibliothek, die coscribe noch nicht hat. Die Karte **Install a Python package** (oder Node.js) nennt sie und sagt, warum. **Install** installiert sie in coscribes eigene Umgebung, die der Rest Ihres Computers nicht nutzt; **Not now** lehnt für diese Unterhaltung ab. Schlägt die Installation fehl, zeigt **Details** die Ausgabe des Installationsprogramms.

## Eine Frage beantworten {#answer-a-question}

Manchmal bittet coscribe Sie, eine Wahl zu treffen, zum Beispiel zwischen zwei Layouts. Wählen Sie eine Option auf der Karte oder tippen Sie Ihre eigene Antwort ins Nachrichtenfeld.
