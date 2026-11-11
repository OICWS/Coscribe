# Switches for files and artifacts, and no cap on a reply's steps (shipped)

Why: the two follow-ups of the simpler Settings page (`2026-11-10-settings-simple.md`). The
maintainer wanted the two switches claude.ai has, and a reply that is not cut off at 150 model
calls: the person stops one that runs on, as in Claude Code and Codex.

## Shipped
- **"Create and edit files"** (Settings › Capabilities, on by default). Off, every tool of
  coscribe's that writes, changes or deletes a file (the `filesystem` and `documents` tools with
  the `WRITE_LOCAL` risk, 52 of them) refuses and tells the model why; reading goes on. A script
  or a command the person approves can still write: each has its own switch, and the row says so.
- **"Artifacts"**, under it (on by default). Off, `write_file` makes no new Doc (a `.md` marked
  `coscribe: doc`), design (`*.design.json`) or dashboard (a page with the dashboard mark); the
  model is told to answer in the conversation or write an Office file. A plain file is written,
  an artifact made earlier can still be changed, and a deck is still built: it is a PowerPoint
  file.
- **How:** `conversation/capability_guard.py` wraps the coordinator's file-writing tools when a
  session builds its agent. A tool keeps its name, signature, docstring and metadata, so the
  tool list the provider caches is the same (decision 0001). `approvals.py` asks the same
  question before a person is asked, so nobody approves a write that is then refused; the
  refusal is audited as `capability_off`. The two values live in `capabilities.json` with the
  others.
- **No cap on steps.** `Settings.max_turns` is unset by default, so a conversation's turn ends
  when the model is done or the person stops it. `COSCRIBE_MAX_TURNS` in `.env` still sets one.
  A scheduled task's run has nobody to stop it, so each task of written instructions is saved
  with its own number (`max_steps`, 150 for a new task and for one the model drafts, 1 to 1000),
  changed under "Most steps" in the task's form and shown on its page; the run's agent is built
  with it, whatever `COSCRIBE_MAX_TURNS` says. A workflow's agent steps keep their own
  `max_steps`. The model's task tools have no parameter for it, so their schemas are unchanged.
  Sub-agents and the reviewer keep their own budgets.
- Tried on `coscribe-web` with DeepSeek: with files off, "write hello.txt" wrote nothing and the
  reply gave the text and named the switch; with artifacts off, "make a Doc" got the plan in
  the conversation and an offer of a Word file.

## Not verified
- The desktop app on Windows.
- A long real task past 150 model calls; the tests cover that no cap is installed.

## Follow-ups
- With Artifacts off, the Artifacts page's "Make something new" still offers a Doc, a design and
  a dashboard; the conversation then says they are turned off.
- A refused write still shows as "Wrote hello.txt" (in the failed colour) in the conversation.
