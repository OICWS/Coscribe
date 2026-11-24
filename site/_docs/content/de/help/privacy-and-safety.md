---
title: Datenschutz und Sicherheit
description: Was Ihren Computer verlässt, wenn Sie Coscribe nutzen, wo Ihre Daten liegen und was seine Aktionen in Schranken hält.
---

Coscribe läuft auf Ihrem PC. Es hat kein Konto und keinen eigenen Server und sendet nichts über Sie oder Ihre Nutzung an seine Entwickler.

## Was Ihren Computer verlässt {#what-leaves-your-computer}

| Geht an | Was | Wann |
|---|---|---|
| Den gewählten Modellanbieter | Ihre Nachrichten, die Teile von Dateien, die Coscribe zum Antworten liest, und die Ergebnisse seiner Werkzeuge | Bei jeder Antwort. Mit einem [Modell auf Ihrem PC](../get-started/providers.md#run-a-model-on-your-pc) bleibt auch das auf Ihrem Computer. |
| Suchmaschinen | Die Suchbegriffe | Wenn Coscribe im Web sucht. Es nutzt kostenlose Suchmaschinen wie DuckDuckGo, ohne Schlüssel. |
| Websites | Gewöhnliche Seitenanfragen | Wenn Coscribe eine Seite öffnet, um die Sie gebeten haben oder die eine Aufgabe braucht. Siehe [Der integrierte Browser](../use/browser.md). |
| Verbundene Dienste | Was das Werkzeug eines Konnektors sendet | Wenn Coscribe diesen [Konnektor](../customize/connectors.md) nutzt. |

Die eigenen Bedingungen des Anbieters bestimmen, was er speichert und wie lange. Lesen Sie sie, bevor Sie ihm Arbeitsdokumente senden.

## Wo Ihre Daten liegen {#where-your-data-is-kept}

Alles andere bleibt auf Ihrem PC:

- Ihre Dateien bleiben, wo sie sind; Coscribe bearbeitet sie an Ort und Stelle.
- Unterhaltungen, geplante Aufgaben, Skills und Einstellungen liegen unter `%APPDATA%\Coscribe`.
- API-Schlüssel und [Secrets](../reference/settings.md#secrets) liegen in der Windows-Anmeldeinformationsverwaltung, nie in einer einfachen Datei.
- Ein Protokoll, wie jede Runde verlief (das Modell, Werkzeugaufrufe, Fehler, Tokens und Zeit, ohne die Worte der Unterhaltung), bleibt zur Fehlerbehebung auf Ihrem PC. Nichts lädt es hoch.

## Was Aktionen in Schranken hält {#what-keeps-actions-in-check}

- **Ordner**: Coscribe schreibt nur in seinen Arbeitsbereich und die anderen Ordner, die Sie erlaubt haben. Siehe [Arbeitsbereiche und Ordner](../workspaces/workspaces.md).
- **Genehmigungen**: Aktionen, die etwas ändern, warten auf Sie, wie es der [Berechtigungsmodus](../use/approvals.md) vorsieht. Eine Datei, die Coscribe mit seinen eigenen Dateiwerkzeugen löscht, landet im Papierkorb.
- **Skripte** laufen in einem isolierten Container, wo Windows es zulässt, beschränkt auf die Ordner des Arbeitsbereichs; wo sich keine Isolation einrichten lässt, sind Skripte aus, sofern Sie nichts anderes wählen. Siehe [Skripte und Isolation](../workspaces/workspaces.md#scripts-and-isolation).
- **Websites**: Was Coscribe im Browser öffnen darf, folgt der Website-Einstellung des Arbeitsbereichs. Siehe [Eine Website erlauben](../use/browser.md#allow-a-site).

> [!IMPORTANT]
> Genehmigungen sind eine Prüfung durch Sie, keine Sandbox. Ein Skript oder Befehl, den Sie genehmigen, kann tun, was Ihr Windows-Konto tun kann, sofern die Isolation es nicht zurückhält. Lesen Sie, was eine Genehmigungskarte sagt, bevor Sie auf **Allow** klicken.

## Worauf Sie achten sollten {#things-to-watch-for}

- Text aus dem Web, einer E-Mail oder einem Dokument kann Anweisungen enthalten, die an eine KI gerichtet sind. Coscribe behandelt Gelesenes als Material, nicht als Anweisung von Ihnen, aber kein Modell ist perfekt: Seien Sie vorsichtig mit **Never ask** und **Auto**, wenn eine Aufgabe liest, was andere geschrieben haben.
- Fügen Sie Skills, Plugins und Konnektoren nur von Personen hinzu, denen Sie vertrauen.
