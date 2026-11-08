# A run page says how it went and what it got, before its steps (shipped)

Why: a run's page led with a banner that said nothing when the run wrote no file, and the text
it wrote sat in a step's output further down (#843; decision 0038).

## Shipped
- The run page follows the task page's Simple / Detailed switch; Detailed is unchanged.
- A result card (`RunSummary.tsx`, `lib/runResult.ts`): how the run stands in one line with what
  can be done (try again, let AI look into it, answer, stop), the files it wrote with Open, the
  text the last finished AI step wrote ("Before it stopped" on a failed run), and one line for
  each step that failed without stopping the run or took more tries.
- The steps in the task page's sentences with their state and time; the step a run waits or
  stopped at opens its card there. The detailed page is folded under Details.
- Tests: `lib/runResult.test.ts`; the run-page e2e specs read the simple view first, then
  switch to Detailed for the step outputs.

## Not verified
- The page on a real Windows machine, and Open on a file there.

## Follow-ups
- If the picked text is often the wrong one, a marker on the step that writes the result.
