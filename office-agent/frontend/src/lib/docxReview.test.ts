import { describe, expect, it } from "vitest";
import { askMessage, commentOn, replyTo, setResolved, settleAllChanges, settleChange, stackCards } from "./docxReview";

const cards = [
  { id: "a", anchor: 100, height: 80 },
  { id: "b", anchor: 120, height: 60 },
  { id: "c", anchor: 400, height: 40 },
];

describe("stackCards", () => {
  it("keeps cards level with their words and pushes an overlapping one down", () => {
    expect(stackCards(cards, null, 8)).toEqual({ a: 100, b: 188, c: 400 });
  });

  it("puts the active card level with its words and moves the ones above out of its way", () => {
    expect(stackCards(cards, "b", 8)).toEqual({ a: 32, b: 120, c: 400 });
  });

  it("pushes the cards after the active one down when they would overlap it", () => {
    const close = [...cards.slice(0, 2), { id: "c", anchor: 130, height: 40 }];
    expect(stackCards(close, "b", 8)).toEqual({ a: 32, b: 120, c: 188 });
  });
});

describe("review actions as operations", () => {
  it("accepts or rejects one change by its id", () => {
    expect(settleChange("7", true)).toEqual([{ op: "accept", change: "7" }]);
    expect(settleChange("7", false)).toEqual([{ op: "reject", change: "7" }]);
  });

  it("accepts or rejects every change", () => {
    expect(settleAllChanges(true)).toEqual([{ op: "accept_all" }]);
    expect(settleAllChanges(false)).toEqual([{ op: "reject_all" }]);
  });
});

describe("comment actions as operations", () => {
  it("replies to a thread with the trimmed text", () => {
    expect(replyTo("3", "  Agreed \n")).toEqual([{ op: "reply", comment: "3", text: "Agreed" }]);
  });

  it("resolves or reopens a thread", () => {
    expect(setResolved("3", true)).toEqual([{ op: "resolve", comment: "3" }]);
    expect(setResolved("3", false)).toEqual([{ op: "reopen", comment: "3" }]);
  });

  it("comments on the selected words with line breaks folded", () => {
    expect(commentOn(" the total\n  price ", "Check")).toEqual([{ op: "comment", on: "the total price", text: "Check" }]);
  });
});

describe("askMessage", () => {
  it("names the file and page and quotes every line of the selection", () => {
    expect(askMessage("report.docx", 2, "Total price\nis 100")).toBe(
      "Question about report.docx, page 2:\n> Total price\n> is 100",
    );
  });
});
