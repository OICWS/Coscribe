import { describe, expect, it } from "vitest";
import { DEFAULT_PINNED, normalizePinned } from "./toolbarItems";

describe("normalizePinned", () => {
  it("falls back to the defaults when nothing usable was stored", () => {
    expect(normalizePinned(null)).toEqual(DEFAULT_PINNED);
    expect(normalizePinned("not json")).toEqual(DEFAULT_PINNED);
    expect(normalizePinned('{"plan":true}')).toEqual(DEFAULT_PINNED);
  });

  it("keeps a stored choice, in the bar's order, without items it does not know", () => {
    expect(normalizePinned('["browser","gone","plan"]')).toEqual(["sidebar", "plan", "browser"]);
  });

  it("keeps an empty list empty, except for the sidebar button, which cannot be unpinned", () => {
    expect(normalizePinned("[]")).toEqual(["sidebar"]);
  });
});
