# 0060: A question card waits in the conversation, not the turn

## Status
Proposed (2026-11-25; OICWS asked for it and chose the behaviour in the project thread).

## Context
`ask_user_question` was an interrupt: the turn waited on the person's answer, and the card was
docked above the message box, covering the end of the conversation. Closing it told the model
"the user closed the questions, don't ask again", so someone reading or busy had to answer or
lose the question, and nothing went on until they did. A single question also had its own text
box, though the message box below does the same.

## Decision
- **The call returns at once.** `ask_user_question` is a plain READ tool, no longer in
  `QUESTION_TOOL_NAMES`; its result says the card is shown and not to guess. The model decides:
  when the rest depends on the answer it ends its turn, when part doesn't it does that part and
  says what waits. The end-of-turn plan check doesn't send open tasks back after a question.
- **The card sits in the conversation** where it was asked, with lettered options and a
  Recommended badge (an option's `recommended`). One question answers on a click and has no
  text box and no Submit; "Or just reply in chat" puts the cursor in the message box. Several
  questions page within the card, each with a line for an answer of the person's own, and
  Submit shows only once every question has an answer. Answered, the card folds to the answer.
- **A click is the person's next message**, starting `[Answers to your question card]`, which
  the page draws as the answered card rather than a bubble.
- **An answer in words** gets a note on the person's message naming the open card
  (`conversation/turn_text.py`). When their words answer every question the model records them
  with `answer_question_card` (a core tool), which closes the card and shows the answers; it
  refuses a partial answer, so the model asks about the rest. An unrelated message leaves the
  card open.
- **A newer card replaces an open one**, which shows "No longer needed".
- `remember` keeps the blocking question card (it saves only on the person's click), drawn the
  same way in the conversation.

## Consequences
- A card's state is rebuilt from the history on every load: the call, then a click's message or
  the model's record. A conversation saved before this shows the old answer from the call's result.
- The tool list grows by `answer_question_card` (fixed and cached, 0001).
- A scheduled or unattended turn that asks leaves the card for the person to answer later.

Retired wording: "This call always pauses for a real person to answer"
