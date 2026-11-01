# 0031: A workflow asks for typed inputs and goes one of several ways

Status: proposed (2026-11-01, kurtosisOC; needs the maintainer's acceptance). Builds on 0028
(the graph stays fixed). Issue #776, batch 1.

## Context
A task that runs monthly needs "last month" without someone typing a date, and a department or a
yes or no without free text a step can't rely on. A branch held one condition and an approval
one `when`, so "over 10,000 or more than 3 new vendors" took two nested branches, and a split by
department took one branch per value. A loop went through every item even when the first match
was all the task wanted. Each gap pushed people to an agent step or a script for plain logic.

## Decision
- **Inputs have kinds.** text, number, date, choice (with its options), yes_no, file, folder.
  - A date's default may be relative (`last_month_start`, `week_start`, ...), worked out on the
    day each run starts (`workflow_spec.inputs`; the frontend mirrors it).
  - A run's value is checked against the kind and refused when it doesn't fit, not guessed.
  - What saving allows never comes from a relative date: it names another day each run.
- **Conditions come as lists with `match`: "all" or "any".** Check, approval `when`, branch and
  a loop's `until` take a list. A list stops at the first condition that settles it, so a later
  one may read what an earlier one rules out. A check step with "all" still reports every one.
- **New comparisons:** not_contains, starts_with, ends_with, empty, before, after (dates).
- **A choice step** goes one of several paths by a value: the first case it equals, as text,
  ignoring case and surrounding spaces, else `otherwise`. After it, a name is readable only if
  every path makes it, as after a branch. A run records the path as `case:N` or `otherwise`.
- **A loop may stop early.** `until` is checked after each pass, with the item and that pass's
  results; when it holds the loop ends and keeps what it collected.
- **No new version.** A workflow saved with one `condition` or `when` loads as a one-item list
  (`current_shape`), and the store hands it out in the current shape.

## Consequences
- The simple view's quick edit can change a condition's value, a path's value, an input's
  default and a loop's limits without the full editor.
- Comparison is a lookup, never an expression: there is still no arithmetic in a condition.
- Parallel steps and a choice by pattern are not part of this; a script step decides those.
