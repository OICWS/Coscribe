# A question left to the model closes the card (shipped)

Why: Collins answered a two-question card with "随便什么内容" (anything). The model went on and
made the file, but never called `answer_question_card`, so the card stayed open at "0 of 2
answered". Decision [0060](../decisions/0060-a-question-card-waits-in-the-conversation-not-the-turn.md).

## Shipped
- The open-card note (`conversation/turn_text.py`) and `answer_question_card`'s description say
  that leaving a question to the model ("anything", "you decide", "随便") settles it: the model
  records the choice it makes and the card closes with "Answered in chat".
- Checked on DeepSeek V4 Pro in the real app: before the change "随便什么内容" left the card open;
  after it, "随便什么内容" and "你看着办吧" each closed the card with the model's choices.

## Not verified
- The desktop app on Windows (the web page was checked on Linux Chromium).
