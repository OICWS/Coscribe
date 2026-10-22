// @vitest-environment jsdom
// jsdom for this file only: these functions read and build DOM nodes, which the config's `node`
// environment (kept for the rest, where it is faster) does not have.
/// <reference types="node" />
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { describe, expect, it } from "vitest";
import { drawSection, textNode, writeTextBack } from "./sectionDom";
import { slideLayouts, type SlideLook } from "../../lib/slideLayouts";
import { boxOf, elementsOf, newElement, parseSection, retag, setNotes, writeSection, type Insert } from "../../lib/slideSource";

const LOOK: SlideLook = { background: "#FFFFFF", text: "#1F2937", muted: "#4B5563", accent: "#C2410C", font: "Calibri" };
const INSERTS: Insert[] = [
  { kind: "text" },
  { kind: "table" },
  ...(["rect", "round-rect", "ellipse", "triangle", "arrow", "line"] as const).map((shape) => ({ kind: "shape" as const, shape })),
  { kind: "picture", src: "assets/picture.png", width: 400, height: 300 },
  { kind: "container", layout: "row" },
  { kind: "container", layout: "column" },
];

/** Every source these functions produce, by a name that says how; `tests/test_slide_sources.py`
 * has the server's own parser and compiler judge them. */
const produced: Record<string, string> = {};
const keep = (name: string, doc: Document) => {
  produced[name] = writeSection(doc);
  return produced[name];
};

const edited = (html: string) => {
  const holder = document.createElement("div");
  holder.innerHTML = html;
  return holder;
};

describe("the ten layouts", () => {
  const layouts = slideLayouts(LOOK);

  it("are ten, each a section the editor can read", () => {
    expect(layouts.map((l) => l.name)).toHaveLength(10);
    for (const layout of layouts) {
      const doc = parseSection(layout.source);
      expect(doc.documentElement.localName).toBe("section");
      keep(`layout ${layout.name}`, doc);
    }
  });

  it("draw one node per element that has a box", () => {
    for (const layout of layouts) {
      const doc = parseSection(layout.source);
      const root = document.createElement("div").attachShadow({ mode: "open" });
      const parts = elementsOf(doc).map(() => ({ kind: "text" as const, box: null, picture: null }));
      const nodes = drawSection(root, doc, parts);
      expect(nodes).toHaveLength(elementsOf(doc).length);
      expect(root.querySelectorAll(".slide")).toHaveLength(1);
    }
  });

  it("draws a table being edited with its header cells centred, as the server draws them", () => {
    const doc = parseSection(
      '<section><table style="left:100px;top:100px;width:800px;height:300px"><tr><th>Month</th><th>Orders</th></tr><tr><td>2026-07</td><td style="text-align:right">50</td></tr></table></section>',
    );
    const root = document.createElement("div").attachShadow({ mode: "open" });
    drawSection(root, doc, [{ kind: "drawing", box: null, picture: null }], 0);
    const align = (selector: string) => (root.querySelector(selector) as HTMLElement).style.textAlign;
    expect(align("th")).toBe("center");
    expect(align("tr:nth-child(2) td:first-child")).toBe("left");
    expect(align("tr:nth-child(2) td:last-child")).toBe("right");
  });

  it("draws a flat line in an svg the browser will paint, which has no zero side", () => {
    const doc = parseSection('<section><x-shape data-shape="line" style="left:120px;top:954px;width:1680px;height:0px;border:1.5px solid #1E2C42"/></section>');
    const root = document.createElement("div").attachShadow({ mode: "open" });
    drawSection(root, doc, [{ kind: "drawing", box: null, picture: null }]);
    const svg = root.querySelector("[data-line] svg");
    expect(svg?.getAttribute("width")).toBe("1680");
    expect(svg?.getAttribute("height")).toBe("1");
    expect(root.querySelector("line")?.getAttribute("y2")).toBe("0");
  });
});

describe("inserts", () => {
  it("add an element with a box to the slide, and the section stays readable", () => {
    for (const insert of INSERTS) {
      const doc = parseSection(slideLayouts(LOOK)[0].source);
      doc.documentElement.append(newElement(doc, insert, "#C2410C"));
      const [added] = elementsOf(doc);
      expect(added.getAttribute("style")).toMatch(/left:\d+px;top:\d+px;width:\d+px;height:\d+px/);
      const name = insert.kind === "shape" ? `shape ${insert.shape}` : insert.kind;
      expect(parseSection(keep(`insert ${name}`, doc))).toBeTruthy();
    }
  });
});

describe("a second insert", () => {
  it("does not start where the first one did", () => {
    const doc = parseSection(slideLayouts(LOOK)[0].source);
    const starts = new Set<string>();
    for (let i = 0; i < 3; i++) {
      const el = newElement(doc, { kind: "text" }, "#C2410C");
      doc.documentElement.append(el);
      starts.add(boxOf(el)!.slice(0, 2).join(","));
    }
    expect(starts.size).toBe(3);
  });
});

describe("writing typed text back", () => {
  const section = (inner: string) => parseSection(`<section style="background:#FFFFFF">${inner}</section>`);
  const box = "left:160px;top:200px;width:800px;height:100px";

  it("turns what the browser adds while typing into the section language's tags", () => {
    const doc = section(`<p style="${box}">old</p>`);
    const [p] = elementsOf(doc);
    writeTextBack(edited('one <b>two</b><div>three</div><font color="#C2410C">four</font><div><br></div>'), p);
    expect(p.innerHTML).toBe('one <b>two</b><br/>three<span style="color:#C2410C">four</span>');
    keep("text back paragraph", doc);
  });

  it("keeps one li per line of a list", () => {
    const doc = section(`<ul style="${box}"><li>a</li></ul>`);
    const [ul] = elementsOf(doc);
    writeTextBack(edited("<li>first</li><li>second <i>x</i></li><li> </li>"), ul);
    expect(Array.from(ul.children).map((li) => li.textContent)).toEqual(["first", "second x"]);
    keep("text back list", doc);
  });

  it("round-trips the text of a drawn element", () => {
    const doc = parseSection(slideLayouts(LOOK)[3].source);
    const root = document.createElement("div").attachShadow({ mode: "open" });
    const nodes = drawSection(root, doc, elementsOf(doc).map(() => ({ kind: "text" as const, box: null, picture: null })));
    const [heading] = elementsOf(doc);
    const before = heading.textContent;
    writeTextBack(textNode(nodes[0])!, heading);
    expect(heading.textContent).toBe(before);
    keep("text back drawn", doc);
  });
});

describe("changing an element's tag and a slide's notes", () => {
  it("moves a paragraph to a list and back without losing its lines", () => {
    const doc = parseSection(`<section><p style="left:0px;top:0px;width:900px;height:200px">one<br/>two<br/>three</p></section>`);
    const list = retag(elementsOf(doc)[0], "ul");
    expect(Array.from(list.children).map((li) => li.textContent)).toEqual(["one", "two", "three"]);
    keep("retag list", doc);
    const back = retag(list, "h2");
    expect(back.localName).toBe("h2");
    expect(back.textContent).toBe("onetwothree");
    keep("retag heading", doc);
  });

  it("adds, changes and removes the speaker notes", () => {
    const doc = parseSection(slideLayouts(LOOK)[3].source);
    setNotes(doc, "Say this first.");
    expect(doc.documentElement.querySelector("aside")?.textContent).toBe("Say this first.");
    expect(elementsOf(doc).some((el) => el.localName === "aside")).toBe(false);
    keep("notes", doc);
    setNotes(doc, "  ");
    expect(doc.documentElement.querySelector("aside")).toBeNull();
  });
});

it("writes the sources it produced for the server to judge", () => {
  const out = process.env.SLIDE_SOURCES_OUT;
  if (!out) return;
  expect(Object.keys(produced).length).toBeGreaterThan(20);
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, JSON.stringify(produced));
});
