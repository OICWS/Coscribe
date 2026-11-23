---
title: Skills and plugins
description: Teach coscribe a way of working once, add skills others made, and turn them on or off.
---

A skill is a set of instructions for one kind of job, such as how your team writes a weekly report. When a job matches a skill's description, coscribe follows it. coscribe comes with some built-in skills, and you can add your own.

## Use a skill

You don't have to do anything: coscribe picks a skill when it fits. To use one on purpose, type <kbd>/</kbd> in the message box and pick it from the list, or type its name after the slash, followed by your request.

## Save a job as a skill

After you've done a job in a conversation, you can keep how it was done:

- Type `/create-skill` followed by a name.
- Or choose **Save as skill** when coscribe offers **Save this job?** after a job of several steps.

You can also start from **Settings** › **Skills** › **Add** › **Create with Coscribe**, which opens a conversation for you to describe the skill.

## Add skills others made

In **Settings** › **Skills**:

- **Discover** lists open-source skills from [github.com/anthropics/skills](https://github.com/anthropics/skills) and [github.com/anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins). Most come as a plugin: a bundle of skills. Open one to see its skills, the connectors it uses and its license; **Add** downloads all of its skills.
- **Add** › **Upload a skill** takes a skill file you were given: a `SKILL.md`, a `.zip`, `.skill` or `.plugin` file.

> [!WARNING]
> A skill is instructions coscribe follows. Add skills only from people you trust, and read one before you use it: open it in **Yours** to see its files.

## Turn skills on or off

**Yours** lists your skills. Open one to read its files, and use its switch to turn it off without deleting it. The menu next to a skill removes it. Removing a skill that came in a plugin removes every skill of that plugin.

## Skills for one folder

A folder can bring its own skills in `.coscribe/skills/`. They apply only in conversations that use that folder, once you've accepted its settings. See [A folder's own notes and rules](../workspaces/folder-settings.md).

## Write a skill by hand

A skill is a folder with a `SKILL.md` file. The file starts with a `name` and a `description`, then the instructions in Markdown:

```markdown
---
name: Weekly report
description: Write the weekly sales report from the order export. Use when asked for the weekly report.
---

1. Read the latest export in Reports/Exports.
2. ...
```

The description decides when coscribe uses the skill, so say what the skill is for and when to use it. This is the same format as Claude Code's skills.
