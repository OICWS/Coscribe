# A step runs several lanes of steps at the same time (shipped)

Why: a task that gathers from several places went through them one after another, though none
needed the others, and a slow site held up the rest (#788, batch 1; decision 0036).

## Shipped
- `workflow_spec`: `ParallelStep` (`kind: "parallel"`, 2 to `MAX_LANES` lanes, failure handling
  like a tool step) and `Lane` (a label and its steps). Saving checks that a lane reads only
  what came before the step, that lanes save different names and have different labels; after
  the step every lane's results can be read. `child_lists` names the lanes `lane:<n>`.
- `workflows/parallel.py`: each lane runs as a `WorkflowRun` of its own on the thread
  `<caller>~<step>~<task id>~<lane>`, from the caller's values (`WorkflowRun.start_from`), all
  at once; lanes that may use the browser take turns. Pauses pass up one at a time, keyed by
  where the lane stopped. A failed lane lets the others end, then the step fails; a retry goes
  on in the failed lanes from the step that failed (a no is asked again), and `settled` counts
  a step that failed on an answer as failed. Test runs guard lane steps that can't be taken
  back; the report lists a failed lane step, not the parallel step as well; the drafter is told
  when to use one. Retrying a lane step through the server resumes the run.
- Frontend: the parallel step in the full editor (`ParallelEditor.tsx`: lane names, adding one,
  taking out an empty one), each lane's own step list, the add-step menu, quick edit, the canvas
  (`ParallelBlock`: lanes side by side between a doubled split and join, stacked past three),
  the run view (each lane's steps under its name, `lib/runArms.ts`), the side panel and the
  canvas's run states.
- Tests: `tests/test_workflow_parallel.py` (8), `tests/web/test_scheduled_parallel.py`,
  `lib/parallelSteps.test.ts`, and the e2e spec `workflow-parallel-steps.spec.ts`.

## Not verified
- On a real Windows machine with a real model: lanes that open sites in the built-in browser,
  and a draft from a conversation that proposes a parallel step.

## Follow-ups
- A lane that waits for another, and lanes over the items of a list, are left out (decision 0036).
