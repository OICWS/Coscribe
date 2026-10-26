# Design note: Word documents written from a spec

Date: 2026-10-26
Area: docs

A design note and a proposed decision (0024) for writing Word documents from a spec (markdown with a
head and a few components), compiled onto a design-system theme and checked without a model, with a
plan step for longer documents. It extends 0013 and 0019 and keeps the .docx the only artifact. It
rests on a survey of articles and projects (legaldoc, json-to-office, the spec-driven development
critique, outline-guided generation) and on Claude's online Docs as read from its tool instructions.
No code changes; the questions for the maintainer are at the end of the note.

Not verified: that Word keeps the component markers across a save; how cheaper models write the
grammar; the cost of the plan step; whether the design score reaches 4.2.
