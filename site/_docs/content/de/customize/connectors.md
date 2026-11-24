---
title: Konnektoren
description: Verbinden Sie Coscribe mit den Diensten, die Sie nutzen, etwa Mail, Kalender oder Projekt-Tracker, und legen Sie fest, was es dort tun darf.
---

Ein Konnektor lässt Coscribe einen anderen Dienst nutzen: Ihre Mails lesen, einen Termin in einen Kalender eintragen, ein Ticket nachschlagen. Konnektoren verwenden das Model Context Protocol (MCP), daher funktioniert jeder MCP-Server, nicht nur die, die Coscribe auflistet.

## Einen Konnektor hinzufügen {#add-a-connector}

Öffnen Sie **Settings** › **Connectors** › **Discover**, wählen Sie den Dienst und klicken Sie auf **Connect**.

- Die meisten gehosteten Dienste bitten Sie, sich anzumelden. Die Anmeldung öffnet sich auf der Seite des Dienstes selbst, in Ihrem Browser, und Sie melden sich nur einmal an. Coscribe sieht Ihr Passwort nie.
- Ein Dienst mit der Markierung **Needs setup** braucht zuerst eine bei ihm registrierte App. Coscribe führt Sie einmalig durch die Einrichtung. Hat jemand das bereits für Ihr Team eingerichtet, bittet **Copy a message for your admin** diese Person um die Einrichtungsdatei.

Coscribe kann einen Konnektor auch in einer Unterhaltung anbieten, wenn Ihre Anfrage einen Dienst braucht, den Sie nicht verbunden haben. Klicken Sie auf der Karte auf **Connect**, und Coscribe macht weiter, sobald die Verbindung steht. **Not now** lässt es dabei; Sie können ihn jederzeit unter **Settings** › **Connectors** verbinden.

## Einen benutzerdefinierten Konnektor hinzufügen {#add-a-custom-connector}

Für einen MCP-Server, der nicht gelistet ist, wählen Sie **Add** › **Add custom connector**, geben ihm einen Namen und dann entweder:

- Geben Sie die **MCP server URL** eines gehosteten Servers ein, mit allen Headern, die er braucht. Um einen Schlüssel in einen Header zu setzen, ohne ihn auszuschreiben, verwenden Sie **Insert a secret**; der Header lautet dann `{{secret:NAME}}`, und der Wert kommt aus [Secrets](../reference/settings.md#secrets).
- Oder wählen Sie **Run a local command instead** und geben Sie den Befehl ein, etwa `npx`, seine Argumente und nötige Umgebungsvariablen. Er läuft als Programm auf diesem Computer, mit Ihren Rechten.

> [!WARNING]
> Ein lokaler Befehl läuft mit allem, was Ihr Windows-Konto tun kann. Fügen Sie nur Server hinzu, denen Sie vertrauen.

## Festlegen, was er tun darf {#choose-what-it-may-do}

Öffnen Sie einen Konnektor unter **Yours**, um seine Werkzeuge zu sehen, aufgeteilt in **Read-only tools** und **Write/delete tools**. Wählen Sie für jedes Werkzeug:

| Wahl | Was passiert |
|---|---|
| **Always allow** | Coscribe verwendet es ohne Nachfrage. |
| **Needs approval** | Coscribe fragt Sie jedes Mal. Siehe [Genehmigungen und Berechtigungsmodi](../use/approvals.md). |
| **Blocked** | Coscribe kann es nicht verwenden. |

Die Seite des Konnektors zeigt auch, ob er verbunden ist. Wenn nicht, verbindet **Retry** erneut, und **Sign in** öffnet die Anmeldeseite des Dienstes.

## Konnektoren für einen Ordner {#connectors-for-one-folder}

Ein Ordner kann in `.coscribe/mcp.json` eigene Konnektoren mitbringen. Sie gelten nur in Unterhaltungen, die diesen Ordner nutzen, sobald Sie seine Einstellungen akzeptiert haben. Siehe [Eigene Notizen und Regeln eines Ordners](../workspaces/folder-settings.md).

## Einen Konnektor in einem Workflow verwenden {#use-a-connector-in-a-workflow}

Die Werkzeuge eines Konnektors können Schritte eines [Workflows](../workflows/workflows.md) sein, und ein Workflow kann starten, wenn in einem Konnektor etwas Neues auftaucht. Siehe [Einen Workflow bei einem Ereignis starten](../workflows/workflows.md#start-on-an-event).
