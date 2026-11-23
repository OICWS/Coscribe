---
title: Workflows
description: Speichern Sie eine Arbeit als feste Schritte, starten Sie sie nach Zeitplan oder bei einem Ereignis, und legen Sie fest, wie viel die KI entscheiden darf, wenn ein Schritt nicht mehr funktioniert.
---

Ein Workflow ist eine Aufgabe aus festen Schritten. Anders als eine geplante Aufgabe, die schriftlichen Anweisungen folgt, führt ein Workflow jedes Mal dieselben Schritte aus und prüft sie während des Laufs, sodass Sie sehen, was er tun wird, bevor er es tut. Zeitplan, Berechtigungen und Laufberichte funktionieren wie bei [geplanten Aufgaben](scheduled-tasks.md).

## Einen Workflow erstellen {#make-a-workflow}

Am einfachsten erledigen Sie die Arbeit einmal in einem Chat und machen dann einen Workflow daraus:

- Wählen Sie **Save as workflow**, wenn coscribe **Save this job?** anbietet, oder im Bereich **Task details**.
- Oder tippen Sie `/saveworkflow` ins Nachrichtenfeld, auf Wunsch gefolgt von einem Namen.

coscribe entwirft die Schritte aus der Unterhaltung. Sehen Sie sie durch und speichern Sie.

Sie können auch bei null anfangen: **Scheduled** › **New task** › **Build a workflow**. Geben Sie einen Namen und einen Zeitplan an, speichern Sie und fügen Sie dann auf seiner Seite die Schritte hinzu.

## Die Workflow-Seite {#the-workflow-page}

Die Seite hat vier Registerkarten:

- **Overview** sagt in einfachen Worten, was der Workflow tut: wann er läuft, woran er arbeitet, wo er anhält und auf Sie wartet und was er berühren darf. **Show the flowchart** zeichnet die Schritte.
- **Steps** listet die Schritte; hier fügen Sie sie hinzu, ändern und ordnen sie. Die Ansicht kann auch ein **Flowchart** sein.
- **Runs** listet vergangene Läufe.
- **Settings** enthält Zeitplan, Arbeitsbereich und Berechtigungen.

**Run now** ist ausgegraut, bis der Workflow Schritte hat. Nimmt der Workflow Eingaben entgegen, etwa eine Datei, fragt er zuerst danach.

## Arten von Schritten {#kinds-of-steps}

**Add a step** bietet diese Arten:

| Schritt | Was er tut |
|---|---|
| **Tool** | Nutzt eines der Werkzeuge von coscribe, ohne Modell. |
| **Script** | Führt ein festes Python-Skript aus, das Sie geprüft haben. |
| **Model** | Ein Modellaufruf, der festgelegte Felder zurückgeben muss. |
| **Agent** | Arbeitet mit Werkzeugen auf ein Ziel hin, innerhalb der von Ihnen gesetzten Grenzen: die Werkzeuge, die er aufrufen, die Ordner, die er ändern, und die Websites, die er öffnen darf. |
| **Check** | Hält den Lauf an, wenn Werte nicht zutreffen. |
| **Approval** | Pausiert, bis Sie genehmigen. |
| **Ask you** | Pausiert, bis Sie Werte ausfüllen, die spätere Schritte verwenden. |
| **Wait** | Pausiert eine Weile, bis zu einer Uhrzeit oder bis eine Datei erscheint. |
| **Remember** | Behält einen Wert für den nächsten Lauf, etwa was bereits erledigt wurde. |
| **Run a task** | Führt eine andere Ihrer Aufgaben als einen Schritt aus und nutzt ihre Ergebnisse. |
| **If / otherwise** | Führt je nach Wert unterschiedliche Schritte aus. |
| **Choose a path** | Mehrere Pfade, ausgewählt nach dem Wert. |
| **At the same time** | Führt 2 bis 6 Bahnen von Schritten gleichzeitig aus und macht dann weiter. |
| **For each** | Wiederholt Schritte für jedes Element einer Liste. |

Für jeden Schritt können Sie wählen, was bei einem Fehler passiert: **Stop the run**, **Skip it and go on** oder **Run other steps instead**. Ein Schritt kann es außerdem eine festgelegte Anzahl von Malen erneut versuchen.

## Wenn ein Schritt nicht mehr funktioniert {#autonomy}

Websites ändern sich, und Dateien unterscheiden sich von Lauf zu Lauf. Die Einstellung **If a step stops working** legt fest, wie viel die KI dann entscheiden darf:

| Stufe | Was passiert |
|---|---|
| **Fixed** | Nur die gespeicherten Schritte laufen. Schlägt einer fehl, hält der Lauf an und meldet es Ihnen. |
| **Self-healing** | Hat sich eine Website geändert, führt die KI diesen Schritt auf der Seite so aus, wie sie jetzt ist. |
| **Proactive** | KI-Schritte entscheiden, wie sie ihren Teil erledigen. Schlägt ein Schritt fehl, darf die KI einige Schritte hinzufügen; solche, die etwas ändern, warten auf Sie. |
| **Autonomous** | Die KI darf die ganze Aufgabe auf ihre eigene Weise erledigen. |

Hat ein Lauf eine Änderung umgangen, kann coscribe aktualisierte Schritte zur Prüfung vorschlagen, damit der nächste Lauf das nicht mehr muss.

## Einen Workflow bei einem Ereignis starten {#start-on-an-event}

Neben den Zeitplänen, die jede Aufgabe hat, kann die **Frequency** eines Workflows sein:

- **Every few minutes**.
- **When a file arrives in a folder**: Wählen Sie den **Folder to watch** und, falls gewünscht, ein **File name pattern**. Jede neue Datei startet einen Lauf, mit der Datei als Dateieingabe des Workflows. Die Option setzt einen Workflow voraus, der eine Datei entgegennimmt.
- **When something new shows up in a connector**: Wählen Sie einen Konnektor und was er gefragt werden soll. coscribe fragt alle paar Minuten, und jedes neue Element startet einen Lauf. Die erste Prüfung betrachtet alles bereits Vorhandene als gesehen.
- **When a program sends it an event**: Ein anderes Programm auf demselben Computer sendet eine Anfrage mit einem Schlüssel an eine Adresse, die coscribe anzeigt. **Wait for a sample** behält das nächste Ereignis, damit Sie auswählen können, welche seiner Felder die Eingaben füllen. Die Adresse nimmt nur Anfragen von Ihrem eigenen Computer an.

Eine Datei, die ankam, während coscribe geschlossen war, startet einen Lauf, wenn coscribe wieder startet.
