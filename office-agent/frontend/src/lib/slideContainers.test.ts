// @vitest-environment jsdom
// jsdom for this file only: these functions read and build DOM nodes.
import { describe, expect, it } from "vitest";
import { boxOnSlide, elementsOf, inStack, parseSection } from "./slideSource";

const SECTION = `<section>
<p style="left:0px;top:0px;width:300px;height:40px">Free</p>
<x-stack data-layout="row" style="left:100px;top:200px;width:900px;height:300px">
  <x-stack style="flex-grow:1"><h3>One</h3><p>First.</p></x-stack>
  <x-stack style="flex-grow:1"><h3>Two</h3></x-stack>
</x-stack>
<aside>Notes</aside>
<p style="left:0px;top:900px;width:300px;height:40px">Last</p>
</section>`;

describe("a section with containers", () => {
  const doc = parseSection(SECTION);
  const els = elementsOf(doc);

  it("numbers its elements in document order, a container before what it holds", () => {
    expect(els.map((el) => el.localName)).toEqual(["p", "x-stack", "x-stack", "h3", "p", "x-stack", "h3", "p"]);
    expect(els[els.length - 1].textContent).toBe("Last");
  });

  it("knows what a container places", () => {
    expect(els.map(inStack)).toEqual([false, false, true, true, true, true, true, false]);
  });

  it("takes the box of what a container places from the layout, and the rest from the element", () => {
    const placed: [number, number, number, number] = [150, 250, 400, 60];
    expect(boxOnSlide(els[3], placed)).toEqual(placed);
    expect(boxOnSlide(els[0], placed)).toEqual([0, 0, 300, 40]);
    expect(boxOnSlide(els[3], null)).toBeNull();
  });
});
