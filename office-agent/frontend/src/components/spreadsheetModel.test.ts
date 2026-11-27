import { describe, expect, it } from "vitest";
import { axis, visible } from "./spreadsheetModel";

describe("visible", () => {
  const rows = axis(100, 20, [], 2);

  it("keeps the frozen rows and draws the scrolled window", () => {
    expect(visible(rows, 200, 100)).toEqual([1, 2, 13, 14, 15, 16, 17]);
  });

  it("draws extra rows on both sides of the window, never past the sheet", () => {
    expect(visible(rows, 200, 100, 3)).toEqual([1, 2, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]);
    expect(visible(rows, 0, 100, 3).slice(0, 4)).toEqual([1, 2, 3, 4]);
    expect(visible(rows, rows.total, 100, 3).at(-1)).toBe(100);
  });
});
