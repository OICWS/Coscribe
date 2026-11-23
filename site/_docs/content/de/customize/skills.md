---
title: Skills und Plugins
description: Bringen Sie coscribe einmal eine Arbeitsweise bei, fügen Sie Skills anderer hinzu und schalten Sie sie ein oder aus.
---

Ein Skill ist eine Sammlung von Anweisungen für eine Art von Arbeit, etwa wie Ihr Team einen Wochenbericht schreibt. Passt eine Arbeit zur Beschreibung eines Skills, folgt coscribe ihm. coscribe bringt einige integrierte Skills mit, und Sie können eigene hinzufügen.

## Einen Skill verwenden {#use-a-skill}

Sie müssen nichts tun: coscribe wählt einen Skill, wenn er passt. Um einen gezielt zu verwenden, tippen Sie <kbd>/</kbd> ins Nachrichtenfeld und wählen ihn aus der Liste, oder tippen seinen Namen nach dem Schrägstrich, gefolgt von Ihrer Anfrage.

## Eine Arbeit als Skill speichern {#save-a-job-as-a-skill}

Nachdem Sie eine Arbeit in einer Unterhaltung erledigt haben, können Sie festhalten, wie sie gemacht wurde:

- Tippen Sie `/create-skill` gefolgt von einem Namen.
- Oder wählen Sie **Save as skill**, wenn coscribe nach einer Arbeit mit mehreren Schritten **Save this job?** anbietet.

Sie können auch unter **Settings** › **Skills** › **Add** › **Create with Coscribe** beginnen; das öffnet eine Unterhaltung, in der Sie den Skill beschreiben.

## Skills anderer hinzufügen {#add-skills-others-made}

Unter **Settings** › **Skills**:

- **Discover** listet Open-Source-Skills aus [github.com/anthropics/skills](https://github.com/anthropics/skills) und [github.com/anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins). Die meisten kommen als Plugin: ein Paket aus Skills. Öffnen Sie eines, um seine Skills, die verwendeten Konnektoren und seine Lizenz zu sehen; **Add** lädt alle seine Skills herunter.
- **Add** › **Upload a skill** nimmt eine Skill-Datei entgegen, die Sie erhalten haben: eine `SKILL.md` oder eine `.zip`-, `.skill`- oder `.plugin`-Datei.

> [!WARNING]
> Ein Skill besteht aus Anweisungen, denen coscribe folgt. Fügen Sie Skills nur von Personen hinzu, denen Sie vertrauen, und lesen Sie einen Skill, bevor Sie ihn verwenden: Öffnen Sie ihn unter **Yours**, um seine Dateien zu sehen.

## Skills ein- und ausschalten {#turn-skills-on-or-off}

**Yours** listet Ihre Skills. Öffnen Sie einen, um seine Dateien zu lesen, und schalten Sie ihn mit seinem Schalter aus, ohne ihn zu löschen. Das Menü neben einem Skill entfernt ihn. Wenn Sie einen Skill entfernen, der aus einem Plugin stammt, werden alle Skills dieses Plugins entfernt.

## Skills für einen Ordner {#skills-for-one-folder}

Ein Ordner kann in `.coscribe/skills/` eigene Skills mitbringen. Sie gelten nur in Unterhaltungen, die diesen Ordner nutzen, sobald Sie seine Einstellungen akzeptiert haben. Siehe [Eigene Notizen und Regeln eines Ordners](../workspaces/folder-settings.md).

## Einen Skill von Hand schreiben {#write-a-skill-by-hand}

Ein Skill ist ein Ordner mit einer `SKILL.md`-Datei. Die Datei beginnt mit einem `name` und einer `description`, danach folgen die Anweisungen in Markdown:

```markdown
---
name: Weekly report
description: Write the weekly sales report from the order export. Use when asked for the weekly report.
---

1. Read the latest export in Reports/Exports.
2. ...
```

Die Beschreibung entscheidet, wann coscribe den Skill verwendet. Schreiben Sie also, wofür der Skill da ist und wann er verwendet werden soll. Das ist dasselbe Format wie bei den Skills von Claude Code.
