# After a job of several steps, coscribe offers to save it as a workflow or skill (shipped)

Why: step 5 of the agentic plan (#819), second part, approved by the maintainer on 2026-11-08. A job done step by step in a conversation (a weekly report, a monthly export) had to be asked for again each time, unless the person knew to look for "Save as workflow" in the side panel or to type /saveskill.

## Shipped
- `conversation/save_offer.py`: at the end of a finished turn (not stopped, not waiting on an approval or a question), the turn's succeeded steps that changed something are counted: a tool whose risk is a local write or something sent out, or a script that left files. With four or more, the side model reads the request and those steps and names the job, or answers that it is a one-off. A named job sends `save_offer` (how many steps the turn took, and the name).
- At most once per conversation (a `<thread>.save-offered` marker in the state folder, so a restart doesn't offer again), and never in a scheduled or workflow run.
- Above the message box: "That took N steps. Save it so you can run it again, or on a schedule?" with Save as workflow (the existing draft flow, named after the job), Save as skill (`/saveskill <name>`) and Not now. Sending a message also puts it away.
- `Settings.save_offers` (`COSCRIBE_SAVE_OFFERS`, on by default) turns it off.
- Tests: `tests/test_save_offer.py` (which steps count, the turn's own steps, the name, once per conversation, a short turn, a one-off, a run, turned off), `frontend/src/state/reducer.test.ts`.

## Not verified
- A real Windows machine.
- How often a small model other than DeepSeek's calls a one-off job repeatable, or the other way round.

## Follow-ups
- A switch for `COSCRIBE_SAVE_OFFERS` (and `COSCRIBE_FOLDER_BRIEFS`) in Settings > Sessions.
