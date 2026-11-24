---
title: Eigene Notizen und Regeln eines Ordners
description: Lassen Sie einen Ordner Coscribe mitteilen, was er enthält, welche Skills und Konnektoren zu verwenden sind und was ohne Nachfrage laufen darf.
---

Ein Ordner kann in einem darin liegenden `.coscribe`-Ordner Anweisungen für Coscribe mitbringen. Coscribe liest sie für jede Unterhaltung, die den Ordner nutzt, sobald Sie sie akzeptiert haben.

## Was ein Ordner enthalten kann {#what-a-folder-can-hold}

| Datei | Wozu sie dient |
|---|---|
| `.coscribe/memory.md` | Notizen, die Coscribe zu Beginn jeder Unterhaltung in diesem Ordner liest: wofür der Ordner da ist, Konventionen, Namen. |
| `.coscribe/skills/<name>/SKILL.md` | [Skills](../customize/skills.md), die nur in diesem Ordner gelten. |
| `.coscribe/settings.json` | Berechtigungsregeln (`allow`, `ask`, `deny`) und Umgebungsvariablen für Skripte. |
| `.coscribe/mcp.json` | [Konnektoren](../customize/connectors.md), die dieser Ordner nutzt. |

Coscribe selbst schreibt nie `memory.md`, `settings.json` oder `mcp.json`; nur Sie bearbeiten sie. Anhänge, die Sie senden, werden in `.coscribe/uploads/` aufbewahrt.

## Die Einstellungen eines Ordners akzeptieren {#accept-a-folders-settings}

Einstellungen eines Ordners können von jedem stammen, der in ihn schreiben kann, daher befolgt Coscribe sie erst, wenn Sie zustimmen. Der Bereich **Task details** zeigt **What Coscribe knows about this folder** mit den Skills, Konnektoren und Regeln, die der Ordner mitbringt, gruppiert als **Runs without asking**, **Always asks** und **Never runs**, sowie etwaige Variablen für Skripte. Klicken Sie auf **Use them**, um sie zu akzeptieren.

Ändert sich eine dieser Dateien außerhalb von Coscribe, fragt es erneut.

## Berechtigungsregeln {#permission-rules}

`.coscribe/settings.json` hat dasselbe Format wie die Einstellungsdatei von Claude Code:

```json
{
  "permissions": {
    "allow": ["write_file(reports/*)"],
    "ask": ["run_background_command"],
    "deny": ["delete_file"]
  },
  "env": {
    "REPORT_REGION": "East"
  }
}
```

Eine Regel ist ein Werkzeugname von Coscribe, ein `*`-Muster aus Namen oder eines von beiden mit einem Muster seines Hauptarguments in Klammern, etwa `write_file(docs/*)`. Die Regeln entscheiden nur über Aktionen, die sonst auf Ihre Genehmigung warten würden. **deny** hat Vorrang vor **ask**, und **ask** vor **allow**.

Einige Grenzen gelten immer:

- Eine Regel erlaubt nie eine Aktion, die Ihren Computer verlässt, etwa das Senden einer Nachricht über einen Konnektor; diese fragen weiterhin.
- Ein einzelnes `*` erlaubt nichts.
- Eine `ask`-Regel fragt auch im Modus **Auto**.

## Variablen für Skripte {#variables-for-scripts}

Die `env`-Werte in `settings.json` werden an Skripte und Befehle im Ordner übergeben. Ein Ordner kann keine Variablen setzen, die ändern, welche Programme laufen oder wohin der Datenverkehr geht, etwa `PATH`, Proxy-Einstellungen oder `PYTHONPATH`.
