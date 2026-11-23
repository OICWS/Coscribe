---
title: Geplante Aufgaben
description: Lassen Sie Coscribe eine Arbeit nach Zeitplan erledigen, etwa ein Morgenbriefing, und lesen Sie den Bericht jedes Laufs.
---

Eine geplante Aufgabe ist eine Arbeit, die Coscribe ohne Sie erledigt: zu einer festen Zeit, jede Stunde oder wenn Sie sie starten. Jeder Lauf ist eine eigene Unterhaltung und endet mit einem Bericht.

Es gibt zwei Arten. Eine **geplante Aufgabe** folgt schriftlichen Anweisungen, das Modell entscheidet also jedes Mal jeden Schritt. Ein **Workflow** führt feste Schritte aus, die Sie gespeichert haben, und prüft sie während des Laufs; siehe [Workflows](workflows.md). Diese Seite behandelt, was beide gemeinsam haben.

## Eine Aufgabe erstellen {#create-a-task}

Öffnen Sie **Scheduled** in der Navigation und dann **New task**:

- **Create with Coscribe** startet einen Chat, in dem Sie die Arbeit beschreiben oder einmal durchgehen. Coscribe entwirft die Aufgabe dann in einer Karte; **Review & save** öffnet sie, damit Sie vor dem Speichern alles ändern können.
- **Set up manually** öffnet das Formular, in dem Sie Name, Anweisungen und Zeitplan selbst eintragen.
- **Build a workflow** startet einen leeren Workflow. Siehe [Workflows](workflows.md).

Nach einer Arbeit in einem Chat bietet Coscribe möglicherweise auch **Save this job?** an. **Save as workflow** macht daraus feste Schritte, die Sie erneut ausführen oder planen können; **Save as skill** behält sie als Anweisungen für das nächste Mal (siehe [Skills](../customize/skills.md)).

## Festlegen, wann sie läuft {#choose-when-it-runs}

**Frequency** kann **Manual** (nur wenn Sie sie starten), **Hourly**, **Daily**, **Weekdays**, **Weekly** oder **Monthly** sein. Tägliche, werktägliche und wöchentliche Läufe erhalten eine Uhrzeit; wöchentliche zusätzlich einen Wochentag. Ein Workflow kann außerdem alle paar Minuten laufen oder wenn etwas passiert; siehe [Einen Workflow bei einem Ereignis starten](workflows.md#start-on-an-event).

Eine Aufgabe hat außerdem einen **Workspace**, der die Ordner und Websites bestimmt, die ihre Läufe nutzen dürfen (siehe [Arbeitsbereiche und Ordner](../workspaces/workspaces.md)), und ein **Model**. **Default model** verwendet das in Ihren Einstellungen festgelegte Modell.

## Festlegen, was sie ohne Sie tun darf {#choose-what-it-may-do-without-you}

Niemand beobachtet einen Lauf, daher legt eine Aufgabe ihre eigenen **Permissions** fest:

| Einstellung | Was passiert |
|---|---|
| **Ask before every action** | Der Lauf pausiert und wartet vor jeder Aktion, die sie braucht, auf Ihre Genehmigung. |
| **Automatically approve** | Der Lauf erstellt und bearbeitet Dateien selbst, pausiert aber, bevor er Code ausführt oder Konnektoren nutzt. |
| **Never ask** | Der Lauf pausiert nie für eine Genehmigung, auch nicht zum Ausführen von Code oder Nutzen von Konnektoren. Ihre Sperrregeln gelten weiterhin. |

**Most steps** beendet einen Lauf nach so vielen Schritten, damit ein fehlgeleiteter Lauf nicht lange weiterläuft.

> [!WARNING]
> Mit **Never ask** kann ein Lauf ohne Nachfrage Code ausführen und Ihre Konnektoren nutzen. Verwenden Sie es nur für eine Aufgabe, deren Anweisungen Sie vertrauen.

## Die App laufen lassen {#keep-the-app-running}

Wenn Sie das Coscribe-Fenster schließen, läuft es im Infobereich der Taskleiste weiter, und Aufgaben laufen weiterhin. Zum Beenden wählen Sie **Quit** am Symbol im Infobereich. Schalten Sie **Keep running in the background** unter **Settings** › **General** aus, beendet das Schließen des Fensters Coscribe, und die Aufgaben stoppen mit.

War ein Lauf fällig, während Coscribe geschlossen war, läuft er einmal, wenn Coscribe wieder startet.

## Die Läufe verfolgen {#follow-the-runs}

Die Seite einer Aufgabe zeigt, wann sie als Nächstes läuft, ihre letzten Läufe und deren Status: **Running**, **Completed**, **Failed**, **Needs approval**, **Waiting** oder **Stopped**. Öffnen Sie einen Lauf, um seine Unterhaltung und seinen Bericht zu sehen. Ein Lauf, der eine Genehmigung braucht, wartet dort auf Sie.

- **Run now** startet sofort einen Lauf, um die Aufgabe auszuprobieren.
- Der Schalter neben dem Status pausiert die Aufgabe oder setzt sie fort.
- Der Stift benennt die Aufgabe um oder ändert, wann sie läuft.

**Notifications** unter **Settings** › **General** legt fest, ob Coscribe Sie nach jedem Lauf benachrichtigt oder nur bei Problemen: einem fehlgeschlagenen Lauf oder einem, der auf Sie wartet. Ein Klick auf eine Benachrichtigung öffnet den Lauf.

## Gedächtnis zwischen Läufen {#remember-between-runs}

Schalten Sie **Remember between runs** auf der Seite einer geplanten Aufgabe ein, und jeder Lauf schreibt Notizen für den nächsten: seinen Fortschritt, wo er aufgehört hat und was sich geändert hat. Ist die Option aus, beginnt jeder Lauf ohne Notizen.
