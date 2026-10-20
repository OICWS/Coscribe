// @vitest-environment jsdom
// jsdom for this file only: drawing builds DOM nodes.
import { describe, expect, it } from "vitest";
import { elementsOf, parseSection } from "../../lib/slideSource";
import { drawSection } from "./sectionDom";

const SECTION = `<section>
<x-stack data-layout="row" style="left:100px;top:200px;width:900px;height:300px">
  <x-stack style="flex-grow:1"><h3>One</h3><p>First.</p></x-stack>
</x-stack>
</section>`;

describe("drawing a section with containers", () => {
  it("draws what a container places where the layout put it", () => {
    const host = document.createElement("div");
    const doc = parseSection(SECTION);
    const els = elementsOf(doc);
    const nodes = drawSection(host.attachShadow({ mode: "open" }), doc, els.map((_, i) => ({ kind: "text", box: i === 2 ? [150, 250, 400, 60] : null, picture: null })));
    const heading = nodes[2] as HTMLElement;
    expect(heading.style.left).toBe("150px");
    expect(heading.style.width).toBe("400px");
    expect(nodes[0]).toBeNull(); // a container with no card of its own draws nothing
  });
});
