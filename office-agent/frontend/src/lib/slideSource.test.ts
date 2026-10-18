import { describe, expect, it } from "vitest";
import { boxIn, dragBox, elementIndexAt, parseStyle, styleText, withBox, type Box } from "./slideSource";

describe("slide source", () => {
  it("reads and writes a style with its box in whole px", () => {
    const style = parseStyle("left:10px; top:20px;width:300.4px;height:40px;Color:#FFF");
    expect(boxIn(style)).toEqual([10, 20, 300.4, 40]);
    expect(styleText(withBox(style, [11.6, 20, 300, 40]))).toBe("left:12px;top:20px;width:300px;height:40px;color:#FFF");
    expect(boxIn(parseStyle("left:0;top:0"))).toBeNull();
  });

  it("picks the topmost element under a point, and lets a hairline be hit", () => {
    const boxes: (Box | null)[] = [[0, 0, 1920, 1080], [100, 100, 200, 50], null, [0, 500, 1920, 2]];
    expect(elementIndexAt(boxes, 150, 120)).toBe(1);
    expect(elementIndexAt(boxes, 900, 900)).toBe(0);
    expect(elementIndexAt(boxes, 900, 505)).toBe(3);
  });

  it("moves, resizes from an edge or corner, and keeps proportions from a corner", () => {
    const box: Box = [100, 100, 200, 100];
    expect(dragBox(box, [0, 0], 10, -5)).toEqual([110, 95, 200, 100]);
    expect(dragBox(box, [1, 0], 50, 99)).toEqual([100, 100, 250, 100]);
    expect(dragBox(box, [-1, -1], 20, 10)).toEqual([120, 110, 180, 90]);
    expect(dragBox(box, [1, 1], 200, 0, true)).toEqual([100, 100, 400, 200]);
    expect(dragBox(box, [1, 0], -500, 0)[2]).toBe(8);
  });
});
