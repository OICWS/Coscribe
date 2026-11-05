"""What a compaction asks the model for, shared by /compact and the automatic compaction
(`runtime_lg/agent.py`). A literal brace in it would break the automatic one's str.format."""

from __future__ import annotations

COMPACT_INSTRUCTIONS = """\
Summarize the conversation transcript below so the work can go on from the summary alone: \
it replaces the transcript. Write a brief for someone picking up the work fresh, not a \
transcript, and keep these sections, writing "None" under one with nothing in it. When the \
transcript opens with an earlier summary, that summary is the record of everything before \
it: carry each of its sections forward, updated, so no request or fact it holds is lost.

## Requests
Every request the user made, in their own words where the wording matters (names, figures, \
formats, tone), in order, and which ones are done.

## Decisions and constraints
What was agreed or ruled out and why: templates, styles, layouts, sources to use or avoid, \
corrections the user made.

## Files
Each file read, created or changed, with its full path and one line on what it holds or what \
changed in it.

## Facts found
Figures, names and results that came from tools (a script's output, a search, a document) and \
are still needed, with where each came from.

## Current work
What was being done when the transcript ends, and the next step.
"""
