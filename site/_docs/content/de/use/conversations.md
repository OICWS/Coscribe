---
title: In einer Unterhaltung arbeiten
description: Nachrichten und Dateien senden, eine Anfrage ergänzen, während coscribe arbeitet, es anhalten und Gesendetes zurücknehmen oder ändern.
---

Alles in coscribe beginnt in einer Unterhaltung. Jede hat ihren eigenen Verlauf, ihr Modell, ihren Berechtigungsmodus und ihre Ordner.

## Nachrichten und Dateien senden {#send-messages-and-files}

Tippen Sie ins Nachrichtenfeld und drücken Sie <kbd>Enter</kbd>. Um eine Datei oder ein Bild anzuhängen, klicken Sie unten links im Nachrichtenfeld auf **+** oder ziehen Sie es ins Fenster. Angehängte Dateien werden im Ordner `.coscribe/uploads/` des Arbeitsbereichs gespeichert, damit coscribe sie später erneut öffnen kann.

## Eine Anfrage während der Arbeit ergänzen {#add-to-a-request-while-it-works}

Sie müssen nicht warten, bis eine Antwort fertig ist. Alles, was Sie senden, während coscribe arbeitet, wird zu einer Notiz, die es vor seinem nächsten Schritt liest, einschließlich Bildern und Dateien. Eine wartende Notiz hat eigene Schaltflächen:

- **Send now** sendet sie sofort.
- **Cancel and edit message** holt sie zurück ins Nachrichtenfeld. Das geht nur, solange das Nachrichtenfeld leer ist.

Wartet coscribe auf eine Karte (eine Frage oder eine Genehmigung), beantwortet das, was Sie tippen, diese Karte: Eine getippte Antwort auf eine Frage ist Ihre Antwort, und eine getippte Antwort auf eine Genehmigung lehnt die Aktion ab und sagt coscribe, warum.

## Eine Antwort anhalten {#stop-a-reply}

Klicken Sie rechts im Nachrichtenfeld auf **Stop**. Was coscribe bereits geschrieben und getan hat, bleibt erhalten, und die Antwort endet mit „Stopped · What should I do instead?“. Die angehaltene Arbeit nimmt es nur wieder auf, wenn Sie darum bitten.

Das Anhalten einer Antwort hält keine Skripte oder Befehle an, die sie im Hintergrund laufen ließ; die Zeile unter der Antwort zeigt, wie viele noch laufen, und öffnet den Bereich **Background tasks**, in dem Sie sie anhalten können.

## Eine Nachricht zurückspulen oder bearbeiten {#rewind-or-edit-a-message}

Fahren Sie mit der Maus über eine gesendete Nachricht, um zu sehen, wann Sie sie gesendet haben, und drei Schaltflächen:

- **Rewind to here** entfernt diese Nachricht und alles danach und setzt ihren Text zurück ins Nachrichtenfeld.
- **Edit** lässt Sie die Nachricht ändern; **Save** entfernt die späteren Runden und sendet den neuen Text.
- **Copy** kopiert den Text.

> [!WARNING]
> Zurückspulen entfernt Runden aus der Unterhaltung, nicht ihre Folgen. Eine Datei, die coscribe geschrieben hat, ein Befehl, den es ausgeführt hat, oder eine Nachricht, die es über einen Konnektor gesendet hat, bleiben, wie sie sind. Die QuickInfo warnt Sie, wenn eine Runde, die Sie entfernen wollen, so etwas getan hat.

Rewind und Edit sind nicht verfügbar, solange eine Antwort läuft oder eine Karte auf Sie wartet, und auch nicht für Nachrichten vor einem `/compact`.

## Eine Unterhaltung kopieren {#copy-a-conversation}

Tippen Sie `/fork`, um die Unterhaltung in eine neue zu kopieren und diese zu öffnen; `/fork Entwurf Q3 B` benennt die Kopie. Beide Unterhaltungen laufen vom selben Punkt aus weiter und arbeiten mit denselben Dateien, eine in der einen geänderte Datei ist also auch für die andere geändert.

## Eine lange Unterhaltung fortführen {#keep-a-long-conversation-going}

Jedes Modell kann nur eine begrenzte Menge auf einmal lesen. Wird eine Unterhaltung lang, tippen Sie `/compact`: coscribe fasst sie zusammen, um Platz zu schaffen, und macht weiter. `/clear` archiviert die Unterhaltung und beginnt eine neue im selben Arbeitsbereich.

## Eine Nebenfrage stellen {#ask-a-side-question}

Der Bereich **Side chat** (die zwei Sprechblasen in der Symbolleiste) beantwortet Fragen zur Unterhaltung, ohne ihr etwas hinzuzufügen, auch während eine Antwort läuft. Er sieht die Unterhaltung so, wie sie gerade ist. Seine Nachrichten bleiben nur erhalten, solange der Bereich geöffnet ist.

## Einfache oder detaillierte Ansicht {#simple-or-detailed-view}

Standardmäßig zeigt eine Unterhaltung jeden Schritt, den coscribe macht. Stellen Sie unter **Settings › General** die **Conversation view** auf **Simple**, um nur die Antwort und eine Zeile zu sehen, die sagt, was coscribe gerade tut, etwa „Reading“ oder „Running commands“. Karten, die Sie brauchen, wie Genehmigungen und Fragen, erscheinen in beiden Ansichten, und ein Wechsel zurück zu **Detailed** zeigt wieder jeden Schritt.
