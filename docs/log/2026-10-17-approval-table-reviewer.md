# The approval table covers the reviewer's own side and a damaged code setting (shipped)

Why: #402 item 6c. The Auto mode rows of `tests/test_approval_decisions.py` hand the decision
a ready verdict, so nothing pinned what the real reviewer code does with an odd answer or an
error, or what it is shown. The code allowance rows never read a damaged Settings > Code file.

## Shipped
- `REPLY_ROWS` (21): the real `review_action` through the real decision. An allow or block
  inside prose, a code fence or text blocks is read; a model error or timeout, an empty reply,
  text that is not JSON, two answers, a decision in another case, a decision that is neither
  word or a boolean, no decision and a list all ask a person (the card says the reviewer gave
  no answer) and refuse when nobody is there. Blocks count; asking does not.
- `ASKED_ROWS` (15): the system prompt, the action with its arguments (cut at 3,000 characters)
  and its kind, the last eight things the user said (blank messages, the assistant's words and
  notices from other conversations are not them), the folders, and the delegated task.
- `CODE_ROWS` 18 to 21: a settings file that is not JSON or not an object, and a policy that is
  not exactly "allow", ask.
- The module docstring names the new tables. `docs/plan.md` step 10 is closed.

## Mutation check
Each change was made temporarily and reverted; no source file is changed. A reviewer error that
approves failed 3 rows; the decision matched in any case 1; the last eight requests made twenty
1; arguments not cut 1; the delegated task dropped 1; a notice taken for the user's words 1;
the extra folders dropped 1; the kind always WRITE_LOCAL 2; a damaged code settings file that
allows 5. Two changes survive and are equivalent: `allow` for anything but "block" (the reply
was already checked to be one of the two words) and the two checks on an unknown stored policy
(`permissions.py` drops it and the caller compares with "allow"), each of which covers the other.

## Not verified
- Windows; a real reviewer model's replies (the fake returns what the row says).
