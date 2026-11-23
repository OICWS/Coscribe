---
title: Excel-Arbeitsmappen
description: Lassen Sie coscribe Tabellen lesen, bereinigen, summieren und abstimmen, und Arbeitsmappen mit Formeln und Diagrammen erstellen.
---

coscribe liest `.xlsx`-Dateien Blatt für Blatt und schreibt echte Arbeitsmappen: Zellen, Formatierungen, Formeln und native Excel-Diagramme.

## Worum Sie bitten können {#what-to-ask-for}

- **Bereinigen und summieren**: „Entferne die Zeilen ohne Lieferadresse und summiere die Beträge pro Lieferant.“
- **Abstimmen**: „Gleiche den Bankauszug mit unserem Hauptbuch ab und liste auf, was nicht übereinstimmt.“
- **Ein Modell aufbauen**: „Erstelle ein 12-Monats-Budget mit einem Übersichtsblatt, das die Abteilungen addiert.“
- **Ein Diagramm erstellen**: „Füge neben der Tabelle ein Säulendiagramm des Umsatzes nach Region hinzu.“

Nennen Sie die Dateien, und die Blätter, wenn eine Arbeitsmappe mehrere hat, und sagen Sie, was das Ergebnis sein soll: eine neue Datei, ein neues Blatt oder eine Änderung am bestehenden.

## Formeln bleiben Formeln {#formulas-stay-formulas}

Hängt ein Wert von anderen Zellen ab, schreibt coscribe ihn als Excel-Formel, damit die Arbeitsmappe weiter funktioniert, wenn Sie eine Zahl ändern. Es berechnet die Formeln außerdem und speichert ihre Ergebnisse in der Datei, sodass die Werte auch in Programmen erscheinen, die beim Öffnen nicht neu berechnen.

## Große oder ungewöhnliche Aufgaben {#large-or-unusual-jobs}

Für Arbeit, die die integrierten Werkzeuge nicht abdecken, kann coscribe ein Python-Skript schreiben (zum Beispiel mit `pandas` und `openpyxl`) und es mit Ihrer Genehmigung ausführen. Siehe [Genehmigungen und Berechtigungsmodi](../use/approvals.md).

> [!TIP]
> Soll coscribe die Konventionen Ihres Teams befolgen, etwa Farben für Eingaben und Ausgaben oder ein Zahlenformat? Schreiben Sie sie in Ihre [Anweisungen](../customize/instructions.md) oder in einen [Skill](../customize/skills.md).
