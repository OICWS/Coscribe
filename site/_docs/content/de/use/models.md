---
title: Modelle, Aufwand und Kontext
description: Wählen Sie das Modell für eine Unterhaltung, legen Sie fest, wie gründlich es nachdenkt, und sehen Sie, wie voll sein Kontext ist.
---

## Ein Modell wählen {#pick-a-model}

Klicken Sie unter dem Nachrichtenfeld auf den Modellnamen, um das Modell zu wechseln. Der Wechsel gilt ab der nächsten Nachricht, und die Unterhaltung behält alles bisher Gesagte. Solange die Auswahl offen ist, wählen die Tasten <kbd>1</kbd> bis <kbd>9</kbd> das Modell mit dieser Nummer.

Die Auswahl listet die Modelle, die Sie für jeden Anbieter unter **Settings** › **Providers** eingeschaltet haben; siehe [Einen Modellanbieter hinzufügen](../get-started/providers.md). Eine neue Unterhaltung beginnt mit dem **Default model** aus **Settings** › **General**.

## Den Aufwand einstellen {#set-the-effort}

Neben dem Modell liegt der Aufwandsregler, eine Skala von **Faster** bis **Smarter**. Mehr Aufwand lässt das Modell länger nachdenken: besser bei schweren Aufgaben, langsamer und teurer. **Medium** ist ein guter Anfang.

Kennt coscribe die eigenen Stufen des Modells, zeigt die Skala diese an, etwa **Low**, **Medium**, **High**, **Extra high** und **Max**. Andernfalls zeigt sie die ganze Skala, und das Modell verwendet die nächstgelegene unterstützte Stufe. Bei einem Modell ohne Aufwandseinstellung ist der Regler ausgegraut.

Ihre Wahl bleibt beim Modellwechsel erhalten: Das neue Modell verwendet die nächstgelegene Stufe, die es hat.

## Den Kontext im Blick behalten {#watch-the-context}

Jedes Modell kann nur eine begrenzte Menge auf einmal lesen: sein Kontextfenster. Sobald eine Unterhaltung begonnen hat, zeigt ein Ring neben dem Nachrichtenfeld, wie viel davon belegt ist. Klicken Sie auf den Ring, um zu sehen, was den Platz einnimmt: die Nachrichten, der System-Prompt, Werkzeuge und Skills sowie der verbleibende freie Platz.

Ist das Fenster etwa zu vier Fünfteln voll, fasst coscribe den früheren Teil der Unterhaltung von selbst zusammen, um weitermachen zu können. Sie können auch `/compact` tippen, um das sofort zu tun. Siehe [Eine lange Unterhaltung fortführen](conversations.md#keep-a-long-conversation-going).

## Kosten niedrig halten {#keep-costs-down}

Sie bezahlen den Anbieter für das, was das Modell liest und schreibt. Ein paar Gewohnheiten helfen:

- Verwenden Sie für Routinearbeit einen niedrigeren Aufwand.
- Beginnen Sie für eine neue Aufgabe eine neue Unterhaltung, statt eine lange fortzusetzen.
- Schalten Sie **Prompt suggestions** und **Background agents** unter **Settings** › **General** aus, wenn Sie sie nicht nutzen; beide verursachen zusätzliche Modellaufrufe.
- Für Arbeit, die Ihren PC nicht verlassen darf oder die Sie oft erledigen, kostet ein [Modell auf Ihrem PC](../get-started/providers.md#run-a-model-on-your-pc) nichts pro Nutzung.
