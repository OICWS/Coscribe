# Workflow drafts, notices, run page and task tabs, from using them (shipped)

Why: what the maintainer ran into using workflows on Windows: a second draft hid the first's
Save, the run page repeated its steps and jumped, the task panel opened itself, a download to an
allowed folder asked to allow `C:\`, and the task page's settings were hard to read.

## Shipped
- **`C:\` asked for:** in the Windows sandbox a script can't see the folders above an allowed
  one, so `os.makedirs(..., exist_ok=True)` climbed to the drive and tried to make it. The guard
  wrapper's `makedirs` (`tools/exec/script_guard.py`) stops at a folder that exists; a blocked
  write with nothing short of a drive or home to offer fails with a pointer to Settings
  (`workflows/step_work.py`) instead of asking for the drive.
- **Drafts:** each workflow's newest draft keeps its card (`currentWorkflowDrafts`: by the task
  it changes, the draft it revises, else its name). A draft the running reply made can't be
  reviewed yet (`draftsInTheWorks`): the model may still test and fix it. Its button is Test again.
- **Notices above the message box** (`NoticeStack`): unsaved drafts and the save offer, two
  shown and the rest behind "Show N more", gray chips, lavender once a draft's test passed. A
  draft saves straight from its notice. Replaces the pinned draft bar.
- **Save box:** the environment is picked under the box, as under the message box.
- **Run page:** the simple view's Details holds inputs and sites, not the steps again; long step
  text is cut with the whole on hover, times line up; a running run's status is one line; the
  waiting card's buttons don't break. A workflow run doesn't open the task panel by itself.
- **Task page:** tabs Overview, Edit steps, Settings, Runs. Compiled graph is gone, with its
  route, `graph_view.py` and the mermaid package. Autonomy is a list of five with a line each;
  a level below what the steps need can't be picked.

## Checked
- `tests/test_script_guard.py` (makedirs with the parents hidden), `test_workflow_permissions.py`
  (no drive offered), a Windows test in `test_isolation.py` (a script makes and writes its allowed
  folder inside the AppContainer); vitest for the draft grouping and notices; e2e specs moved to
  the Settings tab.
- Screenshots against a stub model.

## Not verified
- The Windows sandbox fix on the maintainer's machine (the Windows CI job runs the test).
- The lavender notice and failed-test card against a real model's test runs.
