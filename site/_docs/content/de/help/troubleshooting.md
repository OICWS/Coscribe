---
title: Fehlerbehebung
description: Prüfen Sie mit /doctor, was Coscribe auf Ihrem PC braucht, beheben Sie häufige Probleme und melden Sie ein Problem.
---

## Eine Prüfung ausführen {#run-a-check}

Tippen Sie `/doctor` in einer beliebigen Unterhaltung. Coscribe prüft, was es auf diesem Computer braucht, und zeigt eine Karte mit jedem Ergebnis, Probleme zuerst, und wie sich jedes beheben lässt. Ist die Lösung eine Einstellung, führt ein Link zu deren Seite.

| Prüfung | Was sie untersucht |
|---|---|
| **Model** | Ob das Standardmodell antwortet. Wenn nicht: Prüfen Sie Schlüssel, Adresse und Modellnamen des Anbieters oder das Netzwerk und den [Proxy](../reference/settings.md#general). |
| **Python for scripts** | Ob ein Python für Skripte vorhanden ist. Wenn nicht, laden Sie das von Coscribe unter **Settings** › **Capabilities** herunter. |
| **Node.js for scripts** | Ob `node` und `npm` für Node.js-Skripte installiert sind. Installieren Sie sie bei Bedarf von [nodejs.org](https://nodejs.org). |
| **Office conversion** | Ob Microsoft Office oder LibreOffice vorhanden ist, um Seitenvorschauen zu erstellen und Dokumente umzuwandeln. Ist keines vorhanden, installieren Sie Office oder laden Sie LibreOffice unter **Settings** › **Capabilities** herunter. |
| **Browser** | Ob Microsoft Edge oder Google Chrome für den Browserbereich und Seitenbilder installiert ist. |
| **Script isolation** | Ob Skripte in ihrem isolierten Container laufen können. Bis der Selbsttest besteht, sind Skripte aus; führen Sie ihn in den Einstellungen des Arbeitsbereichs erneut aus. |
| **Command sandbox** | Ob Befehle in der Sandbox laufen. Ist sie nicht eingerichtet, läuft jeder Befehl nach Ihrer Genehmigung als Sie. |

## Häufige Probleme {#common-problems}

### Eine Antwort schlägt fehl oder kommt nie {#a-reply-fails-or-never-comes}

Führen Sie `/doctor` aus und sehen Sie sich **Model** an. Ein abgelaufener Schlüssel, ein falscher Modellname oder ein Netzwerk, das einen Proxy braucht, sind die üblichen Ursachen. Manche Firmennetzwerke sperren KI-Dienste; fragen Sie Ihre IT-Abteilung oder stellen Sie den Proxy unter **Settings** › **General** › **Proxy** ein.

### Coscribe kann eine Datei oder einen Ordner nicht öffnen {#coscribe-cant-open-a-file-or-folder}

Coscribe arbeitet nur in seinem Arbeitsbereich und den Ordnern, die Sie erlaubt haben. Fragt es nach einem anderen Ordner, erlauben Sie ihn oder fügen Sie den Ordner zum Arbeitsbereich hinzu. Siehe [Zugriff auf einen anderen Ordner gewähren](../use/approvals.md#give-access-to-another-folder).

Bearbeiten Sie dieselbe Word-, Excel- oder PowerPoint-Datei, speichern Sie Ihre Änderungen, bevor Sie fragen. Coscribe bemerkt, wenn sich eine Datei seit dem letzten Lesen geändert hat, liest sie erneut und nimmt seine Änderung an Ihrer Fassung vor, sieht aber nur, was Sie gespeichert haben.

### Skripte laufen nicht {#scripts-dont-run}

Stellen Sie sicher, dass **Run scripts** unter **Settings** › **Capabilities** eingeschaltet ist, führen Sie dann `/doctor` aus und sehen Sie sich **Python for scripts** und **Script isolation** an.

### Ein Konnektor funktioniert nicht mehr {#a-connector-stops-working}

Öffnen Sie ihn unter **Settings** › **Connectors**. Steht dort, dass er nicht verbunden ist, klicken Sie auf **Retry**, oder auf **Sign in**, wenn seine Anmeldung abgelaufen ist.

### Eine geplante Aufgabe ist nicht gelaufen {#a-scheduled-task-didnt-run}

Aufgaben laufen nur, solange Coscribe läuft, im Fenster oder im Infobereich. Prüfen Sie, ob **Keep running in the background** unter **Settings** › **General** eingeschaltet ist und die Aufgabe nicht pausiert ist. Ein Lauf, der fällig war, während Coscribe geschlossen war, läuft einmal, wenn es wieder startet. Siehe [Geplante Aufgaben](../workflows/scheduled-tasks.md).

## Ein Problem melden {#report-a-problem}

Melden Sie es auf [GitHub](https://github.com/OICWS/coscribe/issues/new). Schreiben Sie, worum Sie gebeten haben, was stattdessen passiert ist und was `/doctor` anzeigt.

Um zu zeigen, wie eine Runde schiefging, ohne Ihre Worte zu teilen, klicken Sie in der Seitenleiste mit der rechten Maustaste auf die Unterhaltung und wählen Sie **Export a failed turn…**. Die Datei beschreibt, wie die Runde verlief: das Modell, seine Werkzeugaufrufe und Fehlschläge, Tokens und Zeit sowie den Anfang jedes Werkzeugfehlers. Sie enthält keine Worte der Unterhaltung, und nichts wird gesendet: Sie speichern die Datei und entscheiden, wer sie bekommt.

Das Serverprotokoll liegt unter `%APPDATA%\Coscribe\logs\coscribe-server.log`.
