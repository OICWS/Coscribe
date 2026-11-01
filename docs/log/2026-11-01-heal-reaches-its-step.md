# A heal may bring the page to its step, entering only values the run has (#766)

Why: in the healing eval (#764), 5 of 6 failures were the agent rightly refusing to act outside
its one step. The redesign had put a new required field, a Next button or a review page before
the step, and the failure showed only at the step after it. The maintainer chose to widen heals
within guardrails.

## Shipped
- `workflows/healing.py`:
  - The heal agent now gets the loop's current item. To reach its step it may fill a field the
    page now requires, correct a value the page refuses, and press the form's Next, Continue or
    Review. A step that reads from the page is done from a snapshot.
  - `heal_guard` refuses any typed or selected value that isn't in the item or the step's own
    arguments (a date's digits in another order count), and any key that could type one. Told
    only in words, the first widened run picked "Logistics" for a required choice the row
    lacked, and the supplier was filed (`GUESSED`).
  - It resends what an earlier `irreversible` step in the same pass sent only when the page
    refused it, and then a person says yes to every change; other irreversible steps are left
    to their own step.
  - What it did before the step is kept as `prepared`. Such a heal isn't carried to the next
    item.
- `workflows/agent_step.py`: `CallGuard` (confirm every change, refuse a call) replaces the
  `confirm_changes` flag, so the engine stays the same size.
- `workflows/heal_revision.py`: a heal with `prepared` goes to the revision; its renamed
  arguments are still offered as a fix. The revision prompt names what was done before the step.

## Result (14 fixed scenarios, `--autonomy self_healing --mark-submit --keep-heals`, `deepseek:deepseek-flash`)
| | PASS | HEALED | SAFE_STOP | FAILED | GUESSED |
|---|---|---|---|---|---|
| before (#764) | 4 | 2 | 2 | 6 | 0 |
| widened, words only | 4 | 3 | 1 | 5 | 1 |
| widened, with `heal_guard` | 4 | 5 | 2 | 3 | 0 |

All 5 healed runs, once their heals were kept, passed the next run with no heal. No false
success. 19 asks for a person's yes across the 14 scenarios, which the eval answered yes.

Still failing:
- expenses, a cookie banner and a new required field: `browser_type` doesn't take a date input,
  which the saved step sets by script, and the heal has no script tool.
- date format with a decoy draft button (both sites): after correcting the date, the agent
  saved a draft or declined the other submit button. Nothing wrong was filed.

## Not verified
- On Windows.
- A radio button or checkbox clicked without data isn't caught by the guard, only by the prompt:
  a click names a snapshot element, not a value.
