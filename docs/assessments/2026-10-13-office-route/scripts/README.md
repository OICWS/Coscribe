# Scripts of the 2026-10-13 office-route research

Kept so the measurements in `../../2026-10-13-office-route.md` can be repeated and so the
evaluation (phase P0) can start from them. They ran in a scratch directory, not in this
repository: they expect a ppt-master clone and its own virtualenv next to them (paths at the top
of `ablation.py`), `DEEPSEEK_API_KEY`, and for `judge.py` `GEMINI_API_KEY`. Not maintained code.

- `ablation.py <task.md> <cond>...`: conditions A-D (and A2, AL, AN... by first letter); `ABL_EFFORT` sets
  DeepSeek's `reasoning_effort`.
- `route_e.py <task>`: condition E, coscribe's own `write_pptx` / `add_pptx_chart` (office-agent venv).
- `edit_svg.py <run_dir> <name> "<request>"`: an edit through the page sources.
- `judge.py`, `judge_ds.py`: blind judges (Gemini, DeepSeek vision); `aggregate.py`: mean scores.
- `closure.py`: static import closure of a module in ppt-master's scripts.
- `spike_walker.py`: the spike, our walk and packaging around ppt-master's copied element emitter.
- `tasks/`: the two briefs. `research-notes.md`: raw notes taken during the work.
