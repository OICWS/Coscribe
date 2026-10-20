// @vitest-environment jsdom
// jsdom for this file only: these functions change DOM nodes.
import { describe, expect, it } from "vitest";
import { elementsOf, parseSection, styleOf } from "./slideSource";
import { applyTextStyle, setBold, setList, setSize, setUnderline, textValues } from "./slideText";

const HEADING_1 = { id: "heading-1", name: "Heading 1", size: 144, weight: 700, line_height: 1.1, letter_spacing: 0 };
const text = (tag = "p") => elementsOf(parseSection(`<section><${tag} style="left:0px;top:0px;width:600px;height:80px">Words</${tag}></section>`))[0];

describe("a text element's properties", () => {
  it("takes a named style's values, its tag and its mark, and loses the mark when one is changed by hand", () => {
    const el = applyTextStyle(text(), HEADING_1);
    expect(el.localName).toBe("h1");
    expect(styleOf(el, "font-size")).toBe("144px");
    expect(el.getAttribute("data-text-style")).toBe("heading-1");
    setSize(el, 100);
    expect(el.getAttribute("data-text-style")).toBeNull();
    expect(textValues(el).size).toBe(100);
  });

  it("reads the section language's defaults for what the element does not set", () => {
    const values = textValues(text("h2"));
    expect(values.size).toBe(48);
    expect(values.bold).toBe(true);
    setBold(text("h2"), false);
    expect(textValues(text()).bold).toBe(false);
  });

  it("changes a paragraph into a bulleted or numbered list and back, and underlines each item", () => {
    const el = setList(text(), "bullet");
    expect(el.localName).toBe("ul");
    expect(el.children[0].localName).toBe("li");
    const numbered = setList(el, "numbered");
    expect(numbered.localName).toBe("ol");
    expect(numbered.children.length).toBe(1);
    setUnderline(numbered, true);
    expect(textValues(numbered).underline).toBe(true);
    setUnderline(numbered, false);
    expect(textValues(numbered).underline).toBe(false);
    expect(setList(numbered, "none").localName).toBe("p");
  });
});
