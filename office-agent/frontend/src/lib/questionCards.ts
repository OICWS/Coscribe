import type { LogItem } from "../state/reducer";
import type { QuestionSpec } from "../types/wire";

/** ask_user_question doesn't wait (decision 0060): its card stays in the conversation and is
 * answered by a later message. A click sends a message starting with QUESTION_ANSWER_PREFIX; words
 * of the person's own are matched to the card by the model, which records them with ANSWER_TOOL.
 * Both strings are the backend's (tools/bookkeeping/interaction.py). */
const ASK_TOOL = "ask_user_question";
const ANSWER_TOOL = "answer_question_card";
export const QUESTION_ANSWER_PREFIX = "[Answers to your question card]";
const SHOWN_PREFIX = "The questions are on a card";
const SKIPPED = "(skipped)";

/** One answer per question: the chosen label(s) or the person's words; null for one left out. */
export type CardAnswers = (string | null)[];

export type CardState =
  | { status: "open" }
  | { status: "answered"; answers: CardAnswers; inChat: boolean }
  | { status: "replaced" };

type ToolItem = Extract<LogItem, { kind: "tool" }>;

/** An ask_user_question call, drawn as its card rather than as a tool row. */
export interface AskCardEntry {
  kind: "ask_card";
  id: string;
  item: ToolItem;
}

export function isAskCall(item: LogItem): item is ToolItem {
  return item.kind === "tool" && item.toolName === ASK_TOOL;
}

export function isAnswerCall(item: LogItem): item is ToolItem {
  return item.kind === "tool" && item.toolName === ANSWER_TOOL;
}

const text = (value: unknown) => (typeof value === "string" ? value.trim() : "");

/** The call's questions as the card shows them; the model's arguments are not checked by anyone
 * else, so anything malformed is dropped rather than drawn. */
export function questionsOf(item: ToolItem): QuestionSpec[] {
  const raw = item.arguments.questions;
  if (!Array.isArray(raw)) return [];
  return raw.flatMap((q): QuestionSpec[] => {
    if (!q || typeof q !== "object") return [];
    const record = q as Record<string, unknown>;
    const options = (Array.isArray(record.options) ? record.options : []).flatMap((o) => {
      const option: Record<string, unknown> = o && typeof o === "object" ? (o as Record<string, unknown>) : { label: o };
      const label = text(option.label);
      return label ? [{ label, description: text(option.description), recommended: option.recommended === true }] : [];
    });
    const question = text(record.question);
    return question ? [{ question, header: text(record.header), options, multi_select: record.multi_select === true }] : [];
  });
}

/** The message a click sends: what the model reads, and what the card is redrawn from later. */
export function answerMessage(questions: QuestionSpec[], answers: CardAnswers): string {
  const lines = questions.map((q, i) => `${i + 1}. ${q.question} -> ${answers[i] ?? SKIPPED}`);
  return `${QUESTION_ANSWER_PREFIX}\n${lines.join("\n")}`;
}

function answersFromLines(body: string, questions: QuestionSpec[]): CardAnswers {
  const lines = body.split("\n");
  return questions.map((q, i) => {
    const start = `${i + 1}. ${q.question} -> `;
    const line = lines.find((l) => l.startsWith(start));
    const answer = line?.slice(start.length).trim();
    return answer && answer !== SKIPPED ? answer : null;
  });
}

function answersOfChat(item: ToolItem, count: number): CardAnswers {
  const raw = Array.isArray(item.arguments.answers) ? item.arguments.answers : [];
  return Array.from({ length: count }, (_, i) => text(raw[i]) || null);
}

/** A conversation saved before cards stopped waiting has the answer as the call's result. */
function legacyAnswers(result: unknown, questions: QuestionSpec[]): CardAnswers {
  const body = text(result);
  if (questions.length <= 1) return [body && body !== SKIPPED ? body : null];
  return answersFromLines(body, questions);
}

/** Every question card's state, from the whole conversation: a card is open from its call until a
 * click's message or the model's record of an answer in words, and a newer card replaces it. */
export function questionCardStates(items: LogItem[]): Map<string, CardState> {
  const states = new Map<string, CardState>();
  let open: { id: string; questions: QuestionSpec[] } | null = null;
  for (const item of items) {
    if (isAskCall(item)) {
      if (item.result === undefined || item.isError) continue;
      const questions = questionsOf(item);
      if (!text(item.result).startsWith(SHOWN_PREFIX)) {
        states.set(item.id, { status: "answered", answers: legacyAnswers(item.result, questions), inChat: false });
        continue;
      }
      if (open) states.set(open.id, { status: "replaced" });
      states.set(item.id, { status: "open" });
      open = { id: item.id, questions };
    } else if (open && item.kind === "user" && item.text.startsWith(QUESTION_ANSWER_PREFIX)) {
      states.set(open.id, { status: "answered", answers: answersFromLines(item.text, open.questions), inChat: false });
      open = null;
    } else if (open && isAnswerCall(item)) {
      states.set(open.id, { status: "answered", answers: answersOfChat(item, open.questions.length), inChat: true });
      open = null;
    }
  }
  return states;
}
