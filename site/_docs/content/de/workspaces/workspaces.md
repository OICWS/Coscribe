---
title: Arbeitsbereiche und Ordner
description: Legen Sie fest, welche Ordner, Websites, Secrets und Skripte jede Unterhaltung erreichen kann.
---

Ein **Arbeitsbereich** (Workspace) ist der Ordner, in dem eine Unterhaltung arbeitet, zusammen mit dem, was sie darüber hinaus erreichen darf: andere Ordner, Websites, Secrets und Skripte. Jede Unterhaltung nutzt einen Arbeitsbereich. Unterhaltungen, die keinen wählen, nutzen den Arbeitsbereich **Default**.

## Einen Arbeitsbereich für eine Unterhaltung wählen {#pick-a-workspace-for-a-conversation}

Verwenden Sie die Arbeitsbereichsauswahl unter dem Nachrichtenfeld. Sie listet Ihre Arbeitsbereiche und bietet **New workspace** an. Der Arbeitsbereich **Default** wird von jeder Unterhaltung genutzt, die keinen anderen gewählt hat.

## Einen Arbeitsbereich bearbeiten {#edit-a-workspace}

Öffnen Sie **Settings › Workspaces** und wählen Sie **Edit** im Menü **⋯** eines Arbeitsbereichs, oder erstellen Sie einen mit **New**. Der Dialog enthält einen Namen, den Hauptordner **Folder** (neue Dateien, Screenshots und Artefakte landen hier) und eine Zeile pro Art von Zugriff. Jede Zeile zeigt die aktuelle Einstellung und öffnet ihre eigene Seite:

| Seite | Was sie festlegt |
|---|---|
| **Allowed folders** | Andere Ordner, die dieser Arbeitsbereich nutzen darf, jeweils mit ihrem Zugriff. Andere Arbeitsbereiche erreichen sie nicht. |
| **Sites** | Welche Websites er nutzen darf: **None**, **Listed sites** oder **Any site**, und wie der [integrierte Browser](../use/browser.md#allow-a-site) jede gelistete Website behandelt. |
| **Secrets** | Welche Ihrer gespeicherten Secrets er in einer Webanfrage senden darf. Das Modell sieht den Wert eines Secrets nie. |
| **Scripts and commands** | Ob er Python- und Node.js-**Scripts** sowie **Commands** ausführen darf. |
| **Environment variables** | Werte, die an seine Skripte und Befehle übergeben werden. |

Was die Wahl bei **Sites** bedeutet:

- **None**: keine Websuche, keine Webseiten, keine Downloads und keine Browserschritte; Skripte bleiben offline.
- **Listed sites**: Es öffnet, lädt herunter von und nutzt im Browser nur die gelisteten Websites und ihre Subdomains. Die Suche funktioniert weiter; Skripte bleiben offline.
- **Any site**: jede Website. Listen Sie eine Website, um festzulegen, wie der Browser sie nutzt.

## Erlaubte Ordner {#allowed-folders}

Jeder Ordner, den coscribe außerhalb des Hauptordners eines Arbeitsbereichs nutzen darf, steht in einer einzigen Liste, **Allowed folders**, unter **Settings › Workspaces › Manage**. Jeder Ordner dort hat eine Zugriffsstufe (**Read only**, **Read and write** oder **Read, write and delete**). Ein Arbeitsbereich erreicht nur die erlaubten Ordner, die er auf seiner Seite **Allowed folders** auswählt: **Use an allowed folder** wählt einen aus der Liste, und **Add new folder…** fügt einen neuen hinzu, der mit Lese- und Schreibzugriff in die Liste aufgenommen wird.

Entfernen Sie einen Ordner aus **Allowed folders**, wird er aus jedem Arbeitsbereich entfernt. Ein Ordner, der gerade nicht gefunden wird, etwa auf einem abgesteckten Laufwerk, wird markiert und wieder genutzt, sobald er zurück ist.

Braucht eine Unterhaltung einen Ordner, den sie nicht erreicht, fragt sie auf einer Karte; siehe [Zugriff auf einen anderen Ordner gewähren](../use/approvals.md#give-access-to-another-folder).

## Skripte und Isolation {#scripts-and-isolation}

Unter Windows laufen Skripte isoliert: Sie können nur die Ordner der Unterhaltung nutzen, dort keine Dateien löschen oder umbenennen und erreichen das Internet nur, wenn die Einstellung **Sites** des Arbeitsbereichs **Any site** ist. coscribe prüft einmal, ob die Isolation auf Ihrem Computer funktioniert. Ist die Prüfung fehlgeschlagen, sind Skripte aus; **Run scripts without isolation** auf der Seite **Scripts and commands** schaltet sie für diesen Arbeitsbereich wieder ein, mit dem damit verbundenen Risiko.
