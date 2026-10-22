import { describe, expect, it } from "vitest";
import { STROKE_WIDTHS, STROKE_WIDTH, isNegligible, type Shape } from "./annotation";

describe("annotation shapes", () => {
  it("keeps a click as a numbered step but drops a click as a drag shape", () => {
    const at = { x: 10, y: 10 };
    expect(isNegligible({ kind: "step", color: "#e03131", at, number: 1 })).toBe(false);
    expect(isNegligible({ kind: "redact", from: at, to: { x: 11, y: 11 } })).toBe(true);
    expect(isNegligible({ kind: "redact", from: at, to: { x: 80, y: 40 } })).toBe(false);
    const line: Shape = { kind: "line", color: "#000", width: 3, from: at, to: at };
    expect(isNegligible(line)).toBe(true);
  });

  it("offers four widths and starts on the second", () => {
    expect(STROKE_WIDTHS).toHaveLength(4);
    expect(STROKE_WIDTH).toBe(STROKE_WIDTHS[1]);
  });
});
