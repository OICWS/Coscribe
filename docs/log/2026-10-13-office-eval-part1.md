# Office evaluation, part 1: PowerPoint tasks, a runner on the real agent, automatic checks (partly shipped)

Why: decision 0010 says every step of the office route is decided by measurement. Issue #139 asks for
that measurement, PowerPoint first. This part is the tasks, the runner and the checks; the blind judge,
`compare.py` and the baseline numbers are part 2.

## Shipped
- `office-agent/evals/pptx/tasks/`: 10 tasks (the two research briefs; a project proposal with a timeline;
  a product launch with three images; a long report summarised; the user's own template; an edit of an
  existing deck; mixed Chinese and English; a dense 12-row table; a 15-page deck). Each has `brief.md`,
  `inputs/` and `expect.json`. `pptx/make_inputs.py` rebuilds the binary inputs.
- `evals/run.py`: one fresh workspace per task, the brief sent to a real `ChatSessionLG` with
  `run_approval_mode = "skip"`, the produced deck collected, and per task: wall time, model calls, input,
  cached, output and reasoning tokens (read from the model's own responses), cost at the listed DeepSeek
  price, every tool call by name, tool errors. `--check-only` re-checks a finished run without a model.
- `evals/pptx_checks.py`: opens, fact fidelity (tables, groups and chart data included; separators and
  full-width digits folded), numbers on slides that no input has, page count, pictures used, template
  layouts kept, the editability probe with coscribe's own `read_pptx` and `list_pptx_shapes`, the render
  (LibreOffice to PNG) and coscribe's own overflow, overlap and contrast QA.
- `tests/test_evals_pptx.py` (26 tests): the deterministic parts, plus one `real_libreoffice` render test.
  `pytest` gets `pythonpath = ["."]` so tests can import `evals`.
- A trial run of all 10 tasks on `deepseek-flash`, effort `low`, off-peak: every task finished, 3 to 8
  minutes and 0.025 to 0.062 each (listed price units), 31 to 143 tool calls. The numbers belong to part 2;
  they are not the baseline.

## Not verified
- Windows: the runner and the render were run on Linux only.
- The runner's usage count was checked against one run's totals, not against the vendor's invoice.

## Follow-ups
- Part 2: the blind judge, `compare.py`, the baseline run (#139).
- The editability probe cannot fail on a group shape until #135 is fixed and a deck made of groups is
  among the tasks.
