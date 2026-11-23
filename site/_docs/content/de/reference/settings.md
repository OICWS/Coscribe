---
title: Einstellungen
description: Jede Seite der Einstellungen von coscribe und was jede Einstellung bewirkt.
---

Öffnen Sie die Einstellungen über das Zahnrad oben rechts oder mit <kbd>Ctrl</kbd> + <kbd>,</kbd> in der Desktop-App. Das Suchfeld oben findet eine Einstellung nach ihrem Namen.

## General {#general}

| Einstellung | Was sie bewirkt |
|---|---|
| **Theme** | Hell, dunkel oder wie Windows. |
| **Interface font** | Die Schriftart für Menüs, Bereiche und Unterhaltungen: Figtree, die Systemschrift oder OpenDyslexic. |
| **Motion** | **Reduced** reduziert Animationen in gestreamten Antworten und anderswo. |
| **Conversation view** | **Simple** zeigt jede Antwort ohne die Schritte dahinter und eine Zeile, die sagt, was coscribe gerade tut. **Detailed** zeigt jeden Schritt. |
| **What should Coscribe call you?** | Der Name in der Begrüßung auf dem Startbildschirm. |
| **Default model** | Das Modell, mit dem eine neue Unterhaltung beginnt. Jede Unterhaltung kann es in ihrer eigenen Modellauswahl wechseln. |
| **Default mode** | Der [Berechtigungsmodus](../get-started/first-conversation.md#permission-modes), in dem eine neue Unterhaltung beginnt. |
| **Global instructions** | Was coscribe immer wissen soll. Siehe [Anweisungen](../customize/instructions.md). |
| **Prompt suggestions** | Schlägt nach einer Antwort Ihre nächste Nachricht im Nachrichtenfeld vor: <kbd>Enter</kbd> sendet sie, <kbd>Tab</kbd> setzt sie zum Bearbeiten ins Feld. Erhöht Ihren Verbrauch ein wenig. |
| **Background agents** | Lässt coscribe Arbeit an Helfer abgeben, die im Hintergrund laufen, während Sie weiterschreiben. Sie können viel Verbrauch verursachen. |
| **Archive inactive conversations** | Archiviert Unterhaltungen nach 7, 30 oder 90 Tagen ohne Aktivität, oder nie. Eine geöffnete Unterhaltung oder eine mit laufender Arbeit wird nie archiviert. |
| **Keep running in the background** | Beim Schließen des Fensters bleibt coscribe im Infobereich, sodass geplante Aufgaben weiterlaufen. Ist die Option aus, beendet das Schließen des Fensters die App. |
| **Notifications** | **All** (alle Aufgabenläufe), **Problems only** (ein Lauf ist fehlgeschlagen oder wartet auf Sie) oder **Off**. |
| **Draw attention when Coscribe needs you** | Lässt die Taskleistenschaltfläche blinken, wenn eine Antwort fertig ist oder coscribe auf Sie wartet und das Fenster nicht im Vordergrund ist. |
| **Keep computer awake while Coscribe works** | Verhindert, dass der PC während einer Antwort in den Ruhezustand geht, damit lange Aufgaben fertig werden. Der Bildschirm kann sich trotzdem ausschalten, und das Zuklappen versetzt ihn weiterhin in den Ruhezustand. **Keep awake on battery power** tut dasselbe im Akkubetrieb. |
| **Proxy** | Wie coscribe das Internet erreicht: **System**, **Manual** (Adresse, direkt zu erreichende Hosts, Benutzername und Passwort) oder **No proxy**. |

## Workspaces {#workspaces}

Die Liste Ihrer [Arbeitsbereiche](../workspaces/workspaces.md): **New** fügt einen hinzu, und das Menü **⋯** jedes Arbeitsbereichs bearbeitet oder löscht ihn. **Allowed folders** ist die eine Liste der Ordner außerhalb des Hauptordners eines Arbeitsbereichs, jeweils mit ihrem Zugriff; ein Arbeitsbereich erreicht nur die, die er auswählt. Siehe [Erlaubte Ordner](../workspaces/workspaces.md#allowed-folders).

## Providers {#providers}

Die Modelldienste, die Sie verbunden haben, und die jeweils eingeschalteten Modelle. Siehe [Einen Modellanbieter hinzufügen](../get-started/providers.md).

## Capabilities {#capabilities}

| Einstellung | Was sie bewirkt |
|---|---|
| **Create and edit files** | Lässt coscribe Dateien in den Ordnern seines Arbeitsbereichs schreiben und ändern. Ist die Option aus, liest es sie nur und antwortet in der Unterhaltung. |
| **Artifacts** | Docs, Designs und Dashboards, die sich neben der Unterhaltung öffnen. Siehe [Docs, Designs und Dashboards](../office/artifacts.md). |
| **Run scripts** | Für Arbeit, die für die integrierten Werkzeuge zu groß ist, schreibt coscribe ein Python- oder Node.js-Skript und führt es nach Ihrer Genehmigung aus, beschränkt auf die Ordner des Arbeitsbereichs. Siehe [Skripte und Isolation](../workspaces/workspaces.md#scripts-and-isolation). |
| **Run commands** | Befehlszeilen in cmd oder PowerShell, für das, was ein Skript nicht kann, etwa git oder ein Installationsprogramm. Sie genehmigen jede einzeln. **Command sandbox** und **Private folders** legen fest, was ein Befehl erreichen kann. |
| **Chats can hand tasks to Code** | Lässt eine Unterhaltung eine Programmieraufgabe an Codex übergeben, einen Programmier-Agenten. **Model for code** wählt sein Modell; **Change files without asking** lässt ihn bearbeiten, ohne bei jeder Änderung zu fragen. |
| **Python for scripts**, **Packages for scripts** | Welches Python Skripte ausführt, und zusätzliche Python- und Node.js-Bibliotheken, die sie verwenden dürfen. |
| **LibreOffice**, **Codex** | Optionale Downloads, die Sie hier installieren, aktualisieren oder entfernen. LibreOffice erstellt Seitenvorschauen. |

## Secrets {#secrets}

Schlüssel und Tokens, die Sie einmal hinzufügen und dann den Arbeitsbereichen geben, die sie brauchen. coscribe kann ein Secret in einer Webanfrage nur für die Hosts verwenden, die Sie erlauben, und das Modell sieht seinen Wert nie: Er bleibt aus Nachrichten, Werkzeugergebnissen und Protokollen heraus. Secrets werden in der Windows-Anmeldeinformationsverwaltung gespeichert, nie in einer einfachen Datei.

> [!IMPORTANT]
> Das hält den Wert aus dem heraus, was das Modell liest. Es ist kein Schutz gegen ein Programm, das gezielt danach sucht: Alles, was coscribe auf Ihrem PC ausführt, läuft als Sie und könnte den Anmeldeinformationsspeicher selbst lesen.

## Skills, Connectors, Design systems {#skills-connectors-design-systems}

Siehe [Skills und Plugins](../customize/skills.md), [Konnektoren](../customize/connectors.md) und [Designsysteme](../customize/design-systems.md).
