import { describe, expect, it } from "vitest";
import { SLASH_ITEMS, matchingItems } from "./docsSlash";

describe("the '/' menu's lines", () => {
  it("are all there with nothing typed, and narrow by label or by what people call it", () => {
    expect(matchingItems("")).toHaveLength(SLASH_ITEMS.length);
    expect(matchingItems("head").map((i) => i.id)).toEqual(["h1", "h2", "h3"]);
    expect(matchingItems("2").map((i) => i.id)).toEqual(["h2"]);
    expect(matchingItems("ordered").map((i) => i.id)).toEqual(["numbers"]);
    expect(matchingItems("list").map((i) => i.id)).toEqual(["bullets", "numbers"]);
    expect(matchingItems("GRID").map((i) => i.id)).toEqual(["table"]);
    expect(matchingItems("photo").map((i) => i.id)).toEqual(["picture"]);
  });

  it("are none for words that match nothing, so the menu closes", () => {
    expect(matchingItems("zzz")).toEqual([]);
  });
});
