# Question cards sit in the conversation and don't hold the turn (shipped)

Why: a question from `ask_user_question` stopped all work until it was answered, and its card,
docked above the message box, covered the conversation; closing it counted as refusing to answer.
Decision [0060](../decisions/0060-a-question-card-waits-in-the-conversation-not-the-turn.md).

## Shipped
- `ask_user_question` returns at once (no interrupt). The model ends its turn when the rest
  depends on the answer, or does the part that doesn't. Options can be marked `recommended`.
- The card is drawn where it was asked (`frontend/src/components/QuestionCard.tsx`,
  `lib/questionCards.ts`): lettered options, a Recommended badge, "Or just reply in chat". One
  question answers on a click; several page within the card, each with a line of the person's
  own, and Submit shows once all have an answer. Answered, it folds to the answer with a check;
  a newer card marks an open one "No longer needed".
- A click goes out as the person's next message (`[Answers to your question card]`), drawn as
  the card. A message while a card is open carries a note naming it (`conversation/turn_text.py`);
  the model closes the card with the new core tool `answer_question_card` once every question is
  answered in words.
- `remember`'s card, which still waits, is drawn the same way in the conversation; the docked
  panel is gone.
- Checked on DeepSeek V4 Pro in the real app: a single question answered by a click; three
  questions paged and submitted with one typed answer; a card left open through an unrelated
  message, then closed by an answer in words; a request with an independent half, where the model
  wrote `summary.xlsx` and asked only about the deck. `tests/e2e/question-cards.spec.ts` covers
  the card against the stub model.

## Not verified
- The desktop app on Windows (the web page was checked on Linux Chromium).
- Dark mode was not looked at in a screenshot; the card uses the theme's tokens only.

## Follow-ups
- DeepSeek rarely marks an option `recommended`; whether the prompt should ask harder is open.
