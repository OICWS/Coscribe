/** A slide section's source (decision 0015) as the editor changes it: parsed as XML, changed in
 * place, written back whole. The server checks every save, so these only keep the source in the
 * section language's shape. */

/** x, y, width, height in canvas px (1920 × 1080). */
export type Box = [number, number, number, number];

const BOX_NAMES = ["left", "top", "width", "height"] as const;
/** Smaller than this and an element can no longer be grabbed. */
const MIN_SIZE = 8;

export function parseSection(source: string): Document {
  const doc = new DOMParser().parseFromString(source, "application/xml");
  if (doc.querySelector("parsererror") || doc.documentElement.localName !== "section") {
    throw new Error("The slide's source could not be read");
  }
  return doc;
}

export const writeSection = (doc: Document) => new XMLSerializer().serializeToString(doc);

export const STACK = "x-stack";

/** The section's elements in document order, a container before what it holds, as the server
 * numbers its parts: all but the notes. */
export function elementsOf(doc: Document): Element[] {
  const found: Element[] = [];
  const walk = (parent: Element) => {
    for (const el of Array.from(parent.children)) {
      if (el.localName === "aside") continue;
      found.push(el);
      if (el.localName === STACK) walk(el);
    }
  };
  walk(doc.documentElement);
  return found;
}

/** Inside a container: its place comes from the layout, not from its own `left` and `top`. */
export const inStack = (el: Element) => el.parentElement?.localName === STACK;

/** Where an element is on the slide: its own box, or for what a container places, the server's. */
export const boxOnSlide = (el: Element, placed: Box | null | undefined): Box | null =>
  (inStack(el) ? null : boxOf(el)) ?? placed ?? null;

export function parseStyle(text: string): Map<string, string> {
  const style = new Map<string, string>();
  for (const declaration of text.split(";")) {
    const colon = declaration.indexOf(":");
    if (colon > 0) style.set(declaration.slice(0, colon).trim().toLowerCase(), declaration.slice(colon + 1).trim());
  }
  return style;
}

export const styleText = (style: Map<string, string>) => Array.from(style, ([name, value]) => `${name}:${value}`).join(";");

const readStyle = (el: Element) => parseStyle(el.getAttribute("style") ?? "");

/** The style with the box set; whole px, as the section language reads them. */
export function withBox(style: Map<string, string>, box: Box): Map<string, string> {
  const next = new Map(style);
  BOX_NAMES.forEach((name, i) => next.set(name, `${Math.round(box[i])}px`));
  return next;
}

export const boxOf = (el: Element) => boxIn(readStyle(el));

export function boxIn(style: Map<string, string>): Box | null {
  const values = BOX_NAMES.map((name) => Number.parseFloat(style.get(name) ?? ""));
  return values.every(Number.isFinite) ? (values as Box) : null;
}

export const setBox = (el: Element, box: Box) => el.setAttribute("style", styleText(withBox(readStyle(el), box)));

/** The topmost element whose box holds the point: the last in the section's order. */
export function elementIndexAt(boxes: (Box | null)[], x: number, y: number): number | null {
  for (let i = boxes.length - 1; i >= 0; i--) {
    const box = boxes[i];
    if (!box) continue;
    const [left, top, width, height] = box;
    const slackX = width < 12 ? 6 : 0;
    const slackY = height < 12 ? 6 : 0;
    if (x >= left - slackX && x <= left + width + slackX && y >= top - slackY && y <= top + height + slackY) return i;
  }
  return null;
}

/** Which way each of the eight handles pulls: -1 the left/top edge, 1 the right/bottom, 0 neither. */
export const HANDLES: [number, number][] = [
  [-1, -1], [0, -1], [1, -1],
  [-1, 0], [1, 0],
  [-1, 1], [0, 1], [1, 1],
]; // prettier-ignore

/** `box` moved by `dx`, `dy` (handle [0, 0]) or resized by one handle; `keep` holds the
 * proportions from a corner. */
export function dragBox(box: Box, handle: [number, number], dx: number, dy: number, keep = false): Box {
  const [x, y, w, h] = box;
  const [hx, hy] = handle;
  if (hx === 0 && hy === 0) return [x + dx, y + dy, w, h];
  let width = Math.max(MIN_SIZE, w + hx * dx);
  let height = Math.max(MIN_SIZE, h + hy * dy);
  if (keep && hx !== 0 && hy !== 0) {
    const scale = Math.max(width / w, height / h);
    width = Math.max(MIN_SIZE, w * scale);
    height = Math.max(MIN_SIZE, h * scale);
  }
  return [hx < 0 ? x + w - width : x, hy < 0 ? y + h - height : y, width, height];
}

/** The text styles the format bar offers, as the section language writes them. */
export const PRESETS = {
  Title: { tag: "h1", size: null },
  Heading: { tag: "h2", size: null },
  Lead: { tag: "p", size: 32 },
  Body: { tag: "p", size: null },
  Caption: { tag: "p", size: 22 },
} as const;
export type Preset = keyof typeof PRESETS;

/** The preset a text element is closest to. */
export function presetOf(tag: string, size: number | null): Preset {
  if (tag === "h1") return "Title";
  if (tag === "h2" || tag === "h3") return "Heading";
  if (size !== null && size >= 32) return "Lead";
  if (size !== null && size <= 22) return "Caption";
  return "Body";
}

/** Every colour the source names, most used first: the slide's own palette. */
export function sourceColours(source: string): string[] {
  const counts = new Map<string, number>();
  for (const match of source.matchAll(/#[0-9a-fA-F]{6}\b/g)) {
    const colour = match[0].toUpperCase();
    counts.set(colour, (counts.get(colour) ?? 0) + 1);
  }
  return [...counts].sort((a, b) => b[1] - a[1]).map(([colour]) => colour);
}

/** `rgb(r, g, b)` (what the browser reports) as `#RRGGBB`; a hex colour as it is. */
export function hexColour(css: string): string | null {
  const hex = /^#([0-9a-f]{6})$/i.exec(css.trim());
  if (hex) return `#${hex[1].toUpperCase()}`;
  const rgb = /^rgba?\((\d+),\s*(\d+),\s*(\d+)/.exec(css.trim());
  if (!rgb) return null;
  return `#${rgb.slice(1, 4).map((v) => Number(v).toString(16).padStart(2, "0")).join("").toUpperCase()}`;
}

export function setStyle(el: Element, name: string, value: string | null) {
  const style = readStyle(el);
  if (value === null) style.delete(name);
  else style.set(name, value);
  el.setAttribute("style", styleText(style));
}

export const styleOf = (el: Element, name: string) => readStyle(el).get(name) ?? null;

/** `el` as a `tag` element with the same attributes and content, in its place. */
export function retag(el: Element, tag: string): Element {
  if (el.localName === tag) return el;
  const next = el.ownerDocument.createElement(tag);
  for (const attr of Array.from(el.attributes)) next.setAttribute(attr.name, attr.value);
  if (tag === "ul" || tag === "ol") {
    for (const line of lines(el)) next.append(item(el.ownerDocument, line));
  } else if (el.localName === "ul" || el.localName === "ol") {
    Array.from(el.children).forEach((li, i) => {
      if (i) next.append(el.ownerDocument.createElement("br"));
      next.append(...Array.from(li.childNodes));
    });
  } else next.append(...Array.from(el.childNodes));
  el.replaceWith(next);
  return next;
}

/** A paragraph's content split at its line breaks. */
function lines(el: Element): Node[][] {
  const found: Node[][] = [[]];
  for (const node of Array.from(el.childNodes)) {
    if (node instanceof Element && node.localName === "br") found.push([]);
    else found[found.length - 1].push(node);
  }
  return found.filter((line) => line.some((node) => (node.textContent ?? "").trim()));
}

function item(doc: Document, nodes: Node[]): Element {
  const li = doc.createElement("li");
  li.append(...nodes);
  return li;
}

const KIND_LABELS: Record<string, string> = { "x-stack": "Container", "x-chart": "Chart", table: "Table", img: "Picture", "x-shape": "Shape", "x-icon": "Icon", svg: "Drawing" };

/** How a comment names a section's element, as the server names a slide's shapes: `Title "Q3"`. */
export function labelOf(el: Element): string {
  if (KIND_LABELS[el.localName]) return KIND_LABELS[el.localName];
  const words = (el.textContent ?? "").replace(/\s+/g, " ").trim();
  const snippet = words.length <= 32 ? words : `${words.slice(0, 31)}…`;
  const kind = el.getAttribute("id") === "title" ? "Title" : "Text";
  return snippet ? `${kind} "${snippet}"` : kind;
}

/** What the insert buttons add. */
export type Insert =
  | { kind: "text" }
  | { kind: "table" }
  | { kind: "shape"; shape: "rect" | "round-rect" | "ellipse" | "triangle" | "arrow" | "line" }
  | { kind: "picture"; src: string; width: number; height: number }
  | { kind: "container"; layout: "row" | "column" };

const SIZES: Record<Insert["kind"], [number, number]> = { text: [600, 80], table: [960, 240], shape: [400, 240], picture: [800, 600], container: [1200, 360] };

/** The centre of the slide, or the nearest step down and right of it that no element starts at,
 * so a second new object does not land exactly on the first. */
function freeSpot(doc: Document, [x, y, w, h]: Box): Box {
  const taken = elementsOf(doc).map((el) => boxOf(el));
  while (taken.some((b) => b && Math.abs(b[0] - x) < 8 && Math.abs(b[1] - y) < 8)) {
    x += 48;
    y += 64;
  }
  return [x, y, w, h];
}

/** The section element an insert adds, centred on the slide in `colour` where it has one. */
export function newElement(doc: Document, insert: Insert, colour: string): Element {
  let [w, h] = SIZES[insert.kind];
  if (insert.kind === "picture") {
    const scale = Math.min(w / insert.width, h / insert.height, 1);
    [w, h] = [Math.round(insert.width * scale), Math.round(insert.height * scale)];
  }
  if (insert.kind === "shape" && insert.shape === "line") h = 1;
  const box = freeSpot(doc, [Math.round((1920 - w) / 2), Math.round((1080 - h) / 2), w, h]);
  const style = withBox(new Map(), box);
  const el = doc.createElement({ text: "p", table: "table", shape: "x-shape", picture: "img", container: STACK }[insert.kind]);
  if (insert.kind === "text") el.textContent = "Text";
  if (insert.kind === "table") {
    style.set("font-size", "28px");
    style.set("border-color", "#CBD2DC");
    for (let row = 0; row < 3; row++) {
      const tr = el.appendChild(doc.createElement("tr"));
      for (let col = 0; col < 3; col++) {
        const cell = tr.appendChild(doc.createElement(row ? "td" : "th"));
        if (row) continue;
        cell.textContent = "Column";
        cell.setAttribute("style", `background:${colour};color:#FFFFFF`);
      }
    }
  }
  if (insert.kind === "shape") {
    el.setAttribute("data-shape", insert.shape);
    style.set(insert.shape === "line" ? "border" : "background", insert.shape === "line" ? `4px solid ${colour}` : colour);
  }
  if (insert.kind === "container") {
    el.setAttribute("data-layout", insert.layout);
    for (const [name, value] of [["gap", "24px"], ["padding", "24px"], ["background", "#F3F4F6"], ["border-radius", "16px"]]) style.set(name, value);
    for (let i = 0; i < 2; i++) {
      const text = el.appendChild(doc.createElement("p"));
      text.textContent = "Text";
      if (insert.layout === "row") text.setAttribute("style", "flex-grow:1");
    }
  }
  if (insert.kind === "picture") {
    el.setAttribute("src", insert.src);
    style.set("object-fit", "contain");
  }
  el.setAttribute("style", styleText(style));
  return el;
}

/** A colour for a new shape: the slide's most used one that is not its background or white. */
export function accentOf(doc: Document): string {
  const background = hexColour(styleOf(doc.documentElement, "background") ?? "") ?? "";
  const colours = sourceColours(writeSection(doc)).filter((c) => c !== background && c !== "#FFFFFF");
  return colours.find((c) => c !== hexColour(styleOf(doc.documentElement, "color") ?? "")) ?? "#4472C4";
}

/** The section's speaker notes, its `<aside>`; empty text removes them. */
export function setNotes(doc: Document, text: string) {
  const section = doc.documentElement;
  let aside = Array.from(section.children).find((el) => el.localName === "aside") ?? null;
  if (!text.trim()) return aside?.remove();
  if (!aside) aside = section.appendChild(doc.createElement("aside"));
  aside.textContent = text;
}

/** The slide's transition as the section names it ("fade", "push", "magic"), or none. */
export function setTransition(doc: Document, name: string | null) {
  if (name) doc.documentElement.setAttribute("data-transition", name);
  else doc.documentElement.removeAttribute("data-transition");
}

export const setBackground = (doc: Document, colour: string) => setStyle(doc.documentElement, "background", colour);
