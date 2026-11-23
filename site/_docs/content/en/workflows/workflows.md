---
title: Workflows
description: Save a job as fixed steps, start it on a schedule or an event, and choose how much AI may decide when a step stops working.
---

A workflow is a task made of fixed steps. Unlike a scheduled task that follows written instructions, a workflow does the same steps each time and checks them as they run, so you can see what it will do before it does it. Scheduling, permissions and run reports work as for [Scheduled tasks](scheduled-tasks.md).

## Make a workflow

The easiest way is to do the job once in a chat, then make a workflow from it:

- Choose **Save as workflow** when Coscribe offers **Save this job?**, or in the **Task details** panel.
- Or type `/saveworkflow` in the message box, followed by a name if you like.

Coscribe drafts the steps from the conversation. Look them over, then save.

You can also start from nothing: **Scheduled** › **New task** › **Build a workflow**. Give it a name and a schedule, save, then add the steps on its page.

## The workflow page

The page has four tabs:

- **Overview** says what the workflow does in plain words: when it runs, what it works on, where it stops and waits for you, and what it may touch. **Show the flowchart** draws the steps.
- **Steps** lists the steps, where you add, change and reorder them. The view can also be a **Flowchart**.
- **Runs** lists past runs.
- **Settings** holds the schedule, workspace and permissions.

**Run now** is greyed out until the workflow has steps. If the workflow takes inputs, such as a file, it asks for them first.

## Kinds of steps

**Add a step** offers these kinds:

| Step | What it does |
|---|---|
| **Tool** | Uses one of Coscribe's tools, with no model involved. |
| **Script** | Runs a fixed Python script you've reviewed. |
| **Model** | One model call that must return set fields. |
| **Agent** | Works toward a goal with tools, within the limits you set: the tools it may call, the folders it may change and the sites it may open. |
| **Check** | Stops the run unless values hold. |
| **Approval** | Pauses until you approve. |
| **Ask you** | Pauses until you fill in values the later steps use. |
| **Wait** | Pauses for a while, until a time, or until a file appears. |
| **Remember** | Keeps a value for the next run, such as what was already handled. |
| **Run a task** | Runs another of your tasks as one step and uses its results. |
| **If / otherwise** | Runs different steps depending on a value. |
| **Choose a path** | Several paths, picked by what a value is. |
| **At the same time** | Runs 2 to 6 lanes of steps at once, then goes on. |
| **For each** | Repeats steps for every item in a list. |

For each step you can choose what happens if it fails: **Stop the run**, **Skip it and go on**, or **Run other steps instead**. A step can also try again a set number of times.

## When a step stops working {#autonomy}

Websites change and files differ from run to run. The **If a step stops working** setting decides how much AI may decide when that happens:

| Level | What happens |
|---|---|
| **Fixed** | Only the saved steps run. If one fails, the run stops and tells you. |
| **Self-healing** | If a website changed, AI does that step on the page as it is now. |
| **Proactive** | AI steps decide how to do their part. If a step fails, AI may add a few steps; any that change something wait for you. |
| **Autonomous** | AI may do the whole task its own way. |

When a run worked around a change, Coscribe can suggest updated steps for you to review, so the next run doesn't have to.

## Start a workflow on an event {#start-on-an-event}

Besides the schedules every task has, a workflow's **Frequency** can be:

- **Every few minutes**.
- **When a file arrives in a folder**: pick the **Folder to watch** and, if you like, a **File name pattern**. Each new file starts a run, with the file as the workflow's file input. The option needs a workflow that takes a file.
- **When something new shows up in a connector**: pick a connector and what to ask it. Coscribe asks every few minutes, and each new item starts a run. The first check takes what is already there as seen.
- **When a program sends it an event**: another program on the same computer sends a request to an address Coscribe shows, with a key. **Wait for a sample** keeps the next event so you can pick which of its fields fill the inputs. The address only accepts requests from your own computer.

A file that arrived while Coscribe was closed starts a run when Coscribe starts again.
