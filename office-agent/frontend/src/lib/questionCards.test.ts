import { describe, expect, it } from "vitest";
import type { LogItem } from "../state/reducer";
import { answerMessage, questionCardStates, questionsOf, QUESTION_ANSWER_PREFIX } from "./questionCards";
import { groupToolRuns } from "./transcriptGrouping";

const SHOWN = "The questions are on a card in the conversation; the person answers when they choose.";

const ask = (id: string, questions: unknown[], result: unknown = SHOWN): LogItem => ({
  id,
  kind: "tool",
  toolName: "ask_user_question",
  arguments: { questions },
  result,
});
const user = (text: string): LogItem => ({ id: `u-${text}`, kind: "user", text, turnIndex: 0 });
const recorded = (answers: string[]): LogItem => ({
  id: "rec",
  kind: "tool",
  toolName: "answer_question_card",
  arguments: { answers },
  result: "The card is closed and shows their answers.",
});

const audience = {
  question: "Who is it for?",
  options: [{ label: "Management", description: "8 slides", recommended: true }, { label: "Team" }],
};
const colors = { question: "Which colors?", options: ["Brand", "Plain"] };

describe("questionsOf", () => {
  it("reads labels, descriptions and the recommended option, and drops malformed entries", () => {
    const questions = questionsOf(ask("a", [audience, colors, "junk", { options: [] }]) as Extract<LogItem, { kind: "tool" }>);
    expect(questions).toEqual([
      {
        question: "Who is it for?",
        header: "",
        multi_select: false,
        options: [
          { label: "Management", description: "8 slides", recommended: true },
          { label: "Team", description: "", recommended: false },
        ],
      },
      {
        question: "Which colors?",
        header: "",
        multi_select: false,
        options: [
          { label: "Brand", description: "", recommended: false },
          { label: "Plain", description: "", recommended: false },
        ],
      },
    ]);
  });
});

describe("questionCardStates", () => {
  it("keeps a card open until the click's message answers it", () => {
    const card = ask("a", [audience, colors]);
    const questions = questionsOf(card as Extract<LogItem, { kind: "tool" }>);
    expect(questionCardStates([card]).get("a")).toEqual({ status: "open" });
    const click = user(answerMessage(questions, ["Management", "Brand -> dark"]));
    expect(click.kind === "user" && click.text.startsWith(QUESTION_ANSWER_PREFIX)).toBe(true);
    expect(questionCardStates([card, click]).get("a")).toEqual({
      status: "answered",
      answers: ["Management", "Brand -> dark"],
      inChat: false,
    });
  });

  it("stays open through an unrelated message and closes on the model's record of an answer in words", () => {
    const items = [ask("a", [audience]), user("what time is it?")];
    expect(questionCardStates(items).get("a")).toEqual({ status: "open" });
    expect(questionCardStates([...items, user("for my boss"), recorded(["Management"])]).get("a")).toEqual({
      status: "answered",
      answers: ["Management"],
      inChat: true,
    });
  });

  it("marks an open card replaced when a newer one is asked", () => {
    const states = questionCardStates([ask("a", [audience]), ask("b", [colors])]);
    expect(states.get("a")).toEqual({ status: "replaced" });
    expect(states.get("b")).toEqual({ status: "open" });
  });

  it("shows an older conversation's answer, which came back as the call's result", () => {
    expect(questionCardStates([ask("a", [audience], "Team")]).get("a")).toEqual({ status: "answered", answers: ["Team"], inChat: false });
  });

  it("has no card for a call still running or failed", () => {
    const running = { ...ask("a", [audience]), result: undefined } as LogItem;
    expect(questionCardStates([running]).has("a")).toBe(false);
  });
});

describe("groupToolRuns", () => {
  it("draws a question as its card and hides the record of an answer in words", () => {
    const entries = groupToolRuns([ask("a", [audience]), recorded(["Team"])]);
    expect(entries.map((e) => e.kind)).toEqual(["ask_card"]);
  });
});
