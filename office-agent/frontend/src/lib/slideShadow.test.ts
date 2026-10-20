// @vitest-environment jsdom
// jsdom for this file only: these functions change DOM nodes.
import { describe, expect, it } from "vitest";
import { DEFAULT_SHADOW, readShadow, setShadow } from "./slideShape";
import { elementsOf, parseSection } from "./slideSource";

const shape = () => elementsOf(parseSection('<section><x-shape data-shape="rect" style="left:0px;top:0px;width:100px;height:100px"/></section>'))[0];

describe("a shape's shadow", () => {
  it("is none until one is set, and reads back what was written", () => {
    const el = shape();
    expect(readShadow(el)).toBeNull();
    setShadow(el, { x: 2, y: 8, blur: 24, colour: "#112233", opacity: 0.4 });
    expect(el.getAttribute("style")).toContain("box-shadow:2px 8px 24px #112233 0.4");
    expect(readShadow(el)).toEqual({ x: 2, y: 8, blur: 24, colour: "#112233", opacity: 0.4 });
  });

  it("takes the shadow off with null, and never writes a negative blur", () => {
    const el = shape();
    setShadow(el, { ...DEFAULT_SHADOW, blur: -5 });
    expect(readShadow(el)?.blur).toBe(0);
    setShadow(el, null);
    expect(el.getAttribute("style")).not.toContain("box-shadow");
  });

  it("reads a shadow written without an opacity as the engine draws it", () => {
    const el = shape();
    el.setAttribute("style", "left:0px;top:0px;width:100px;height:100px;box-shadow:0px 4px 10px #000000");
    expect(readShadow(el)?.opacity).toBe(0.35);
  });
});
