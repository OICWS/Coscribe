import { describe, expect, it } from "vitest";
import { LINE_HEIGHT, clamp, familyName, isBold } from "./slideText";

describe("the text properties' values", () => {
  it("names a font by the first family of its stack", () => {
    expect(familyName("Microsoft YaHei, Arial")).toBe("Microsoft YaHei");
    expect(familyName("'Noto Sans SC', sans-serif")).toBe("Noto Sans SC");
    expect(familyName("Arial")).toBe("Arial");
  });

  it("reads a weight as bold from 600 up, or by name, and falls back when there is none", () => {
    expect(isBold("700", false)).toBe(true);
    expect(isBold("bold", false)).toBe(true);
    expect(isBold("400", true)).toBe(false);
    expect(isBold(null, true)).toBe(true);
    expect(isBold(null, false)).toBe(false);
  });

  it("keeps a typed value inside what the section language accepts", () => {
    expect(clamp(0.5, LINE_HEIGHT.min, LINE_HEIGHT.max)).toBe(1);
    expect(clamp(9, LINE_HEIGHT.min, LINE_HEIGHT.max)).toBe(2.5);
    expect(clamp(1.4, LINE_HEIGHT.min, LINE_HEIGHT.max)).toBe(1.4);
  });
});
