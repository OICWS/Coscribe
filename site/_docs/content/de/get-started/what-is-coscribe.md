---
title: Was ist coscribe
description: Ein Büroassistent, der auf Ihrem PC läuft und bearbeitbare Word-, Excel- und PowerPoint-Dateien erstellt.
---

coscribe ist ein KI-Büroassistent für Windows. Sagen Sie in einem Satz, was Sie brauchen, und es liest Ihre Tabellen und Dokumente und erstellt die fertige Datei: einen Vertrag mit Änderungsverfolgung und Kommentaren, eine Berichtspräsentation mit Diagrammen, eine abgestimmte Excel-Arbeitsmappe.

Es ist Open Source (MIT-Lizenz) und kostenlos. Sie zahlen nur für den Modelldienst, den Sie wählen.

## Was es kann {#what-it-can-do}

- **Excel**: Daten lesen, bereinigen, zusammenfassen und abstimmen; Formeln und Diagramme schreiben.
- **Word**: Dokumente entwerfen und überarbeiten und Änderungen mit Änderungsverfolgung und Kommentaren markieren, damit andere sie prüfen können.
- **PowerPoint**: Daten und Material in eine Präsentation verwandeln, mit der Vorlage und den Farben Ihres Unternehmens, falls vorhanden.
- **PDF**: Inhalte durchsuchen, extrahieren und ordnen.
- **Das Web**: Websites in einem integrierten Browser öffnen, Formulare ausfüllen und Tabellen speichern.
- **Workflows**: Speichern, was eine Unterhaltung getan hat, als feste Schritte, und es mit einem Klick oder nach Zeitplan erneut ausführen.

## Was es von anderen KI-Werkzeugen unterscheidet {#how-it-differs-from-other-ai-tools}

**Ihre Dateien bleiben auf Ihrem PC.** coscribe hat keinen eigenen Cloud-Dienst. Nur was das Modell lesen muss, geht an den von Ihnen gewählten Modellanbieter; mit einem Modell, das über Ollama auf Ihrem eigenen Computer läuft, verlässt nichts den Rechner.

**Sie wählen das Modell.** Claude, GPT und Gemini sind integriert. DeepSeek, Kimi, GLM, Qwen, Doubao und jeder andere Dienst mit OpenAI-kompatibler API funktionieren, sobald Sie Adresse und API-Schlüssel eingeben. Siehe [Einen Modellanbieter hinzufügen](providers.md).

**Es fragt, bevor es etwas ändert.** Vier Berechtigungsmodi reichen von „frag mich vor jedem Schritt“ bis „lass ein Prüfmodell Routinearbeit für mich genehmigen“. In jedem Modus schreibt es nur in die Ordner, die Sie erlaubt haben. Siehe [Ihre erste Unterhaltung](first-conversation.md#permission-modes).

**Es liefert fertige Dateien, keine Entwürfe.** Nachdem coscribe eine Datei geschrieben hat, rendert es sie und sieht sich das Ergebnis an, um Layout und Inhalt zu prüfen, statt Ihnen einen Textblock zu geben.

## Systemvoraussetzungen {#system-requirements}

- Windows 10 oder Windows 11.
- Ein API-Schlüssel eines Modelldienstes, oder Ollama bzw. LM Studio auf Ihrem PC.

> [!NOTE]
> coscribe gibt es nur für Windows. Eine Mac- oder Linux-Version gibt es noch nicht.
