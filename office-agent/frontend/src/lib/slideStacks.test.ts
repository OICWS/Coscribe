// @vitest-environment jsdom
// jsdom for this file only: these functions read and change DOM nodes.
import { describe, expect, it } from "vitest";
import { elementsOf, inStack, parseSection, styleOf, type Box } from "./slideSource";
import { dropTarget, moveInto, moveOut, setDirection, siblingOf, stackSlots } from "./slideStacks";

const SECTION = `<section>
<p style="left:0px;top:0px;width:300px;height:40px">Free</p>
<x-stack data-layout="row" style="left:100px;top:200px;width:900px;height:300px">
  <x-stack style="flex-grow:1"><h3>One</h3></x-stack>
  <x-stack style="flex-grow:1"><h3>Two</h3></x-stack>
</x-stack>
</section>`;
// document order: free p, row, card 1, h3 One, card 2, h3 Two
const BOXES: (Box | null)[] = [
  [0, 0, 300, 40],
  [100, 200, 900, 300],
  [100, 200, 440, 300],
  [110, 210, 420, 40],
  [560, 200, 440, 300],
  [570, 210, 420, 40],
];

describe("where a dragged element would land", () => {
  const doc = parseSection(SECTION);
  const els = elementsOf(doc);

  it("is the innermost container under the point, before the children whose middle is past it", () => {
    const slots = stackSlots(doc, BOXES, null);
    expect(slots.map((s) => s.node)).toEqual([1, 2, 4]);
    expect(dropTarget(slots, 50, 20)).toBeNull(); // over the free text, not a container
    expect(dropTarget(slots, 300, 400)).toMatchObject({ node: 2, at: 1 }); // in card 1, below its heading
    const between = dropTarget(slots, 545, 480); // the gap between the cards
    expect(between).toMatchObject({ node: 1, at: 1 });
    expect(between?.line[0]).toBeCloseTo(550 - 2); // a vertical line in the gap
    expect(dropTarget(slots, 300, 212)).toMatchObject({ node: 2, at: 0 }); // above the heading's middle
  });

  it("leaves the dragged element, and any container inside it, out", () => {
    const slots = stackSlots(doc, BOXES, els[2]); // dragging card 1
    expect(slots.map((s) => s.node)).toEqual([1, 4]);
    expect(slots[0].children).toHaveLength(1); // the row now holds only card 2
  });
});

describe("moving an element", () => {
  it("takes a free text box into a column as a child that sizes itself", () => {
    const doc = parseSection(SECTION);
    const els = elementsOf(doc);
    moveInto(els[0], els[2], 1);
    expect(els[0].parentElement).toBe(els[2]);
    expect(styleOf(els[0], "left")).toBeNull();
    expect(styleOf(els[0], "width")).toBeNull();
    expect(styleOf(els[0], "height")).toBeNull();
    expect(els[2].lastElementChild).toBe(els[0]);
  });

  it("takes a free text box into a row with its width and a share of the room", () => {
    const doc = parseSection(SECTION);
    const els = elementsOf(doc);
    moveInto(els[0], els[1], 0);
    expect(els[1].firstElementChild).toBe(els[0]);
    expect(styleOf(els[0], "width")).toBe("300px");
    expect(styleOf(els[0], "height")).toBeNull();
  });

  it("moves a child to another place in the same container without losing its size", () => {
    const doc = parseSection(SECTION);
    const els = elementsOf(doc);
    moveInto(els[2], els[1], 1); // card 1 after card 2
    expect(Array.from(els[1].children)).toEqual([els[4], els[2]]);
    expect(styleOf(els[2], "flex-grow")).toBe("1");
  });

  it("takes a child out onto the slide at a box, without what the container gave it", () => {
    const doc = parseSection(SECTION);
    const els = elementsOf(doc);
    moveOut(els[3], [40, 600, 420, 40]);
    expect(inStack(els[3])).toBe(false);
    expect(els[3].parentElement).toBe(doc.documentElement);
    expect(styleOf(els[3], "left")).toBe("40px");
    expect(elementsOf(doc).at(-1)).toBe(els[3]);
  });
});

describe("changing a container", () => {
  it("fits what it holds to its new direction", () => {
    const doc = parseSection(SECTION);
    const els = elementsOf(doc);
    // card 1 holds a column of text; as a row, the text takes a share of the room
    setDirection(els[2], true);
    expect(els[2].getAttribute("data-layout")).toBe("row");
    expect(styleOf(els[3], "flex-grow")).toBe("1");
    setDirection(els[2], false);
    expect(els[2].getAttribute("data-layout")).toBe("column");
    expect(styleOf(els[3], "flex-grow")).toBeNull();
    expect(styleOf(els[3], "width")).toBeNull();
  });

  it("finds the element after or before another among its parent's, leaving notes out", () => {
    const doc = parseSection(
      '<section><p style="left:0px;top:0px;width:9px;height:9px">A</p><aside>n</aside><p style="left:0px;top:0px;width:9px;height:9px">B</p></section>',
    );
    const [a, b] = elementsOf(doc);
    expect(siblingOf(a, 1)).toBe(b);
    expect(siblingOf(b, -1)).toBe(a);
    expect(siblingOf(a, -1)).toBeNull();
    expect(siblingOf(b, 1)).toBeNull();
  });
});
