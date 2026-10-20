import { describe, expect, it } from "vitest";
import { lineBetween, lineEnds } from "./slideLine";

describe("a line's ends", () => {
  it("are the box's corners the direction joins", () => {
    expect(lineEnds([10, 20, 100, 50], false)).toEqual([[10, 20], [110, 70]]);
    expect(lineEnds([10, 20, 100, 50], true)).toEqual([[10, 70], [110, 20]]);
  });

  it("give the same box and direction back whichever end is dragged", () => {
    for (const rises of [false, true]) {
      const [a, b] = lineEnds([10, 20, 100, 50], rises);
      expect(lineBetween(a, b)).toEqual({ box: [10, 20, 100, 50], rises });
      expect(lineBetween(b, a)).toEqual({ box: [10, 20, 100, 50], rises });
    }
  });

  it("turn when an end is dragged past the other", () => {
    expect(lineBetween([100, 100], [40, 160])).toEqual({ box: [40, 100, 60, 60], rises: true });
    expect(lineBetween([100, 100], [40, 40])).toEqual({ box: [40, 40, 60, 60], rises: false });
    expect(lineBetween([100, 100], [180, 100])).toEqual({ box: [100, 100, 80, 0], rises: false });
  });
});
