# 0038: A run page says how it went and what it got, before its steps

Status: proposed (2026-11-08, kurtosisOC; agreed with the maintainer in the project thread).
Issue #833. Follows 0037, which it does not change.

## Context
A person opening a run wants to know whether it finished, what it got and whether they need to
do anything. The run page led with a banner that, on a run that wrote no file, said nothing;
the text a run wrote sat in a step's output further down, and every AI step's fields were open.

## Decision
- The run page follows the task page's Simple / Detailed switch (`coscribe.taskView`, one
  setting for both). Detailed is the run page as it was.
- Simple opens on a **result card**: one line on how the run stands ("Done in 57s", "Waiting
  for your OK at ...", "Stopped at ..." with its reason in a sentence, "Running: ..." with
  Stop), the files it wrote, and the text it wrote: the longest text the last finished AI step
  handed on, picked by that rule, not by a marker on the step. A failed run shows that text
  too, under "Before it stopped". What went differently without stopping the run (a step
  skipped after it failed, a step that took more tries) is one line each.
- Under it, the **steps** in the task page's sentences, each with how it went and its time; a
  lane, the arm a branch took and a loop's progress are indented. The step the run waits at or
  stopped at opens its card there.
- Everything the detailed page shows is under **Details**, folded, and not drawn until opened,
  so a waiting step is answered in one place.

## Consequences
- Nothing new is stored and no model is called: the card reads the run's own records.
- A task whose result is a number rather than text shows no text; the steps and Details still
  have it. If the rule picks the wrong text often, the next step is a marker on the step.
