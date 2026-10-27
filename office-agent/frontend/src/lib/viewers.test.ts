import { describe, expect, it } from "vitest";
import { isDesign, isDocMarkdown, isViewable } from "./viewers";

describe("viewers", () => {
  it("shows an HTML page as a design, and a lone SVG as the picture file it is", () => {
    expect(isDesign("icons.html")).toBe(true);
    expect(isDesign("out/Icons.HTM")).toBe(true);
    expect(isDesign("mark.svg")).toBe(false);
    expect(isViewable("mark.svg")).toBe(false);
    expect(isViewable("icons.html")).toBe(true);
  });

  it("opens a Markdown file in the viewer, which says when it is not a Doc", () => {
    expect(isDocMarkdown("plan.MD")).toBe(true);
    expect(isViewable("notes/plan.md")).toBe(true);
    expect(isDocMarkdown("plan.mdx")).toBe(false);
  });
});
