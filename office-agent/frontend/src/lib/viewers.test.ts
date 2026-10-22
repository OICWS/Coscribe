import { describe, expect, it } from "vitest";
import { isDesign, isViewable } from "./viewers";

describe("viewers", () => {
  it("shows an HTML page as a design, and a lone SVG as the picture file it is", () => {
    expect(isDesign("icons.html")).toBe(true);
    expect(isDesign("out/Icons.HTM")).toBe(true);
    expect(isDesign("mark.svg")).toBe(false);
    expect(isViewable("mark.svg")).toBe(false);
    expect(isViewable("icons.html")).toBe(true);
  });
});
