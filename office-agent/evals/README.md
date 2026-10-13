# Office evaluation

Decision 0010 (`docs/decisions/0010-office-files-are-compiled-from-whole-page-sources.md`) says each
step of the office route is decided by measurement. This is the measurement: real tasks, sent to
coscribe's real agent, checked automatically, with cost and time recorded. Part 1 covers PowerPoint.
It calls a model, so it is run by hand and is not part of CI; only its deterministic parts are tested
(`tests/test_evals_pptx.py`). It changes nothing under `src/`.

## Run

```bash
cd office-agent
export DEEPSEEK_API_KEY=...            # the default model is deepseek:deepseek-flash
python -m evals.run --route current --tasks all --out evals/runs/baseline
python -m evals.run --tasks 01,07 --out evals/runs/try          # some tasks
python -m evals.run --check-only --out evals/runs/baseline      # re-check, no model calls
```

Long runs go off-peak on DeepSeek (weekdays 9:00-12:00 and 14:00-18:00 Beijing time cost double;
see `CLAUDE.md`). The default reasoning effort is `low` (`--effort none` leaves the model's own).
`evals/runs/` is gitignored.

## A task

`pptx/tasks/<NN-slug>/` holds:

- `brief.md`: what a user would type.
- `inputs/`: files copied into the task's fresh workspace (the brief names them).
- `expect.json`: `facts` (each must appear in the deck; a list inside is alternative spellings),
  `pages` (`[min, max]`), and optionally `absent` (text an edit must remove), `allowed_numbers`
  (numbers the deck may carry that no input has), `pictures_min`, `template` (an input deck whose
  layouts the result must keep).

`pptx/make_inputs.py` rebuilds the binary inputs (images, the deck to edit, the template copy).

## What a run writes

Under `--out`, one folder per task: `result.json` (status, wall time, model calls, input / cached /
output / reasoning tokens, cost, every tool call by name, tool errors, the agent's last message),
`checks.json`, `workspace/` (inputs and what the agent made) and `render/` (one PNG per page); and
`summary.md` / `summary.json` for the whole run.

How a session is built: `ChatSessionLG` with the configured model and the built-in skills, in a
throwaway workspace, `run_approval_mode = "skip"` (a scheduled run's tier: every gated call goes
ahead and nobody is asked). A question the agent puts to the user is answered with "decide it
yourself" and counted. Usage comes from the model's own responses, not from the UI events.

## Checks (`pptx_checks.py`)

| Check | What it says |
|---|---|
| `opens` | python-pptx opens the file |
| `facts` | every fact in `expect.json` is on a slide (tables, groups and chart data included); `absent` text is gone |
| `inventions` | numbers on slides that appear in no input (page numbers and integers up to 31 are skipped); a list to read, not a failure: a sum the model computed is listed too |
| `pages` | page count inside the range |
| `editability` | coscribe's own tools can work on the deck: every slide has a title that `read_pptx` shows, and `list_pptx_shapes` returns for every slide (a deck made of groups crashes it today: #135) |
| `render` | LibreOffice to PDF to one PNG per page |
| `layout` | coscribe's own QA: words past the page edge, overlapping text boxes, low contrast, slides with no visual element |
| `pictures`, `template` | the images were used; the user's template layouts were kept |

## Not in this part

The blind judge, the comparison of two runs and the baseline numbers come in part 2.
