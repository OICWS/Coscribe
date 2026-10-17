import { describe, expect, it } from "vitest";
import { stackCards } from "./docxReview";

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
