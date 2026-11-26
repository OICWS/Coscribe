# A question left to the model closes the card (shipped)

Why: Collins answered a two-question card with "随便什么内容" (anything). The model went on and
made the file, but never called `answer_question_card`, so the card stayed open at "0 of 2
answered". Decision [0060](../decisions/0060-a-question-card-waits-in-the-conversation-not-the-turn.md).

## Shipped
- The open-card note (`conversation/turn_text.py`) and `answer_question_card`'s description say
  that leaving a question to the model ("anything", "you decide", "随便") settles it: the model
  records the choice it makes and the card closes with "Answered in chat".
- When their words settle only some questions, the model asks about the rest in a sentence, not
  with a new card, and the same card closes with every answer once they reply.
- Checked on DeepSeek V4 Pro in the real app: before the change "随便什么内容" left the card open;
  after it, "随便什么内容" and "你看着办吧" each closed the card with the model's choices, as did "都行，你觉得合适就好", "Whatever you think is
  best." and a half-delegated answer. "就做 Q3 销售数据吧" (only the first of two) was followed by a
  question in chat, and the reply closed the one card with both answers (twice).

## Not verified
- The desktop app on Windows (the web page was checked on Linux Chromium).
