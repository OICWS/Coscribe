import { useContext } from "react";
import { answerMessage, questionsOf, type CardAnswers, type CardState } from "../../lib/questionCards";
import type { LogItem } from "../../state/reducer";
import { QuestionCardView } from "../QuestionCard";
import { QuestionActionsContext, QuestionCardStates, type QuestionActions } from "./contexts";

/** An ask_user_question call's card; nothing until its call has returned. */
export function AskCard({ item }: { item: Extract<LogItem, { kind: "tool" }> }) {
  const state = useContext(QuestionCardStates).get(item.id);
  const actions = useContext(QuestionActionsContext);
  if (!state) return null;
  const questions = questionsOf(item);
  return <QuestionCardView questions={questions} state={state} onAnswer={(answers) => actions?.answer(questions, answers)} />;
}

/** remember's question, which holds its turn until it's answered. */
export function PendingQuestionCard({ item }: { item: Extract<LogItem, { kind: "question" }> }) {
  const actions = useContext(QuestionActionsContext);
  const state: CardState =
    item.status === "pending"
      ? { status: "open" }
      : { status: "answered", answers: item.reply !== undefined ? [item.reply] : (item.answers ?? item.questions.map(() => null)), inChat: item.reply !== undefined };
  return <QuestionCardView questions={item.questions} state={state} onAnswer={(answers) => actions?.answerPending(item.id, answers)} />;
}

/** A click on an ask_user_question card is sent as the person's message; remember's answer goes to
 * the turn waiting on it. */
export function questionActions(send: (text: string) => void, answerPending: (id: string, answers: CardAnswers) => void): QuestionActions {
  return { answer: (questions, answers) => send(answerMessage(questions, answers)), answerPending };
}
