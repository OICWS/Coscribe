---
title: Scheduled tasks
description: Have coscribe do a job on a schedule, such as a morning briefing, and read the report of each run.
---

A scheduled task is a job coscribe does without you: at a set time, every hour, or when you start it. Each run is its own conversation, and it ends with a report.

There are two kinds. A **scheduled task** follows written instructions, so the model decides each step every time. A **workflow** runs fixed steps you saved, checked as they run; see [Workflows](workflows.md). This page covers what both share.

## Create a task

Open **Scheduled** in the navigation, then **New task**:

- **Create with Coscribe** starts a chat for you to describe the job, or to walk through it once. coscribe then drafts the task in a card; **Review & save** opens it so you can change anything before you save.
- **Set up manually** opens the form, where you write the name, the instructions and the schedule yourself.
- **Build a workflow** starts an empty workflow. See [Workflows](workflows.md).

After a job you did in a chat, coscribe may also offer **Save this job?**. **Save as workflow** turns it into fixed steps you can rerun or schedule; **Save as skill** keeps it as instructions for next time (see [Skills](../customize/skills.md)).

## Choose when it runs

**Frequency** can be **Manual** (only when you start it), **Hourly**, **Daily**, **Weekdays**, **Weekly** or **Monthly**. Daily, weekday and weekly runs take a time; weekly runs also take a day. A workflow can also run every few minutes, or when something happens; see [Start a workflow on an event](workflows.md#start-on-an-event).

A task also has a **Workspace**, which decides the folders and sites its runs may use (see [Workspaces](../workspaces/workspaces.md)), and a **Model**. **Default model** uses the model set in your settings.

## Choose what it may do without you

Nobody watches a run, so a task sets its own **Permissions**:

| Setting | What happens |
|---|---|
| **Ask before every action** | The run pauses and waits for your approval before any action that needs it. |
| **Automatically approve** | The run creates and edits files on its own, but pauses before running code or using connectors. |
| **Never ask** | The run never pauses for approval, including for running code and using connectors. Your blocking rules still apply. |

**Most steps** ends a run after that many steps, so a run that goes wrong can't go on for long.

> [!WARNING]
> With **Never ask**, a run can run code and use your connectors without asking. Use it only for a task whose instructions you trust.

## Keep the app running

Closing the coscribe window keeps it running in the tray, so tasks still run. To quit, choose **Quit** from the tray icon. If you turn off **Keep running in the background** in **Settings** › **General**, closing the window quits coscribe, and tasks stop with it.

If a run was due while coscribe was closed, it runs once when coscribe starts again.

## Follow the runs

A task's page shows when it runs next, its recent runs and their status: **Running**, **Completed**, **Failed**, **Needs approval**, **Waiting** or **Stopped**. Open a run to see its conversation and its report. A run that needs approval waits there for you.

- **Run now** starts a run at once, to try the task out.
- The switch next to the status pauses the task, or resumes it.
- The pencil renames the task or changes when it runs.

**Notifications** in **Settings** › **General** chooses whether coscribe tells you when each run finishes, or only about problems: a run that failed or is waiting for you. Clicking a notification opens the run.

## Let runs remember {#remember-between-runs}

Turn on **Remember between runs** on a scheduled task's page, and each run writes notes for the next one: its progress, where it left off and what changed. With it off, every run starts without notes.
