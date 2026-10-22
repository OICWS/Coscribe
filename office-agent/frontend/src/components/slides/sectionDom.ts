import { PICTURE_MARGIN, type SlidePart } from "../../lib/slideEditing";
import { boxOnSlide, elementsOf, hexColour, parseStyle, type Box } from "../../lib/slideSource";

/** A section drawn as the browser's own elements, the way the compiler lays it out: each
 * element in its box, text in its own tag, everything else as the server's picture of it. Drawn
 * in a shadow root, so neither the app's styles nor the slide's reach the other. */

const SHEET = `
.slide { position: relative; width: 1920px; height: 1080px; overflow: hidden; }
.box { position: absolute; box-sizing: border-box; display: flex; flex-direction: column; }
.box > * { margin: 0; padding: 0; overflow-wrap: break-word; }
h1 { font-size: 64px; font-weight: 700; line-height: 1.15; }
h2 { font-size: 48px; font-weight: 700; line-height: 1.15; }
h3 { font-size: 36px; font-weight: 700; line-height: 1.2; }
p, ul, ol { font-size: 28px; font-weight: 400; line-height: 1.35; }
li { margin-left: 1.1em; }
li + li { margin-top: 0.35em; }
img { position: absolute; display: block; }
`;

/** Styles that place and fill an element's box; the rest style its text. */
const BOX_STYLES = new Set(["left", "top", "width", "height", "padding", "background"]);
const TEXT_TAGS = new Set(["h1", "h2", "h3", "p", "ul", "ol"]);
const INLINE_TAGS = new Set(["b", "strong", "i", "em", "u", "span", "br", "li"]);
const JUSTIFY: Record<string, string> = { top: "flex-start", middle: "center", bottom: "flex-end" };

/** Draws `doc` into `root` and returns each element's node, in the section's order. */
export function drawSection(root: ShadowRoot, doc: Document, parts: SlidePart[], editing: number | null = null): (HTMLElement | null)[] {
  const sheet = document.createElement("style");
  sheet.textContent = SHEET;
  const slide = document.createElement("div");
  slide.className = "slide";
  const section = parseStyle(doc.documentElement.getAttribute("style") ?? "");
  applyStyle(slide, new Map([...section].filter(([name]) => ["background", "font-family", "color"].includes(name))));
  if (!section.has("background")) slide.style.background = "#ffffff";
  const nodes = elementsOf(doc).map((el, i) => {
    const node = drawElement(el, parts[i], i === editing);
    if (node) slide.append(node);
    return node;
  });
  root.replaceChildren(sheet, slide);
  return nodes;
}

/** `editable`: a table drawn here, with typeable cells, in place of the server's picture of it. */
function drawElement(el: Element, part: SlidePart | undefined, editable: boolean): HTMLElement | null {
  const style = parseStyle(el.getAttribute("style") ?? "");
  const box = boxOnSlide(el, part?.box);
  if (!box) return null;
  if (TEXT_TAGS.has(el.localName)) {
    const outer = document.createElement("div");
    outer.className = "box";
    applyStyle(outer, new Map([...style].filter(([name]) => BOX_STYLES.has(name))));
    placeNode(outer, box);
    outer.style.justifyContent = JUSTIFY[style.get("vertical-align") ?? "top"] ?? "flex-start";
    const inner = copyText(el);
    applyStyle(inner, new Map([...style].filter(([name]) => !BOX_STYLES.has(name) && name !== "vertical-align")));
    outer.append(inner);
    return outer;
  }
  if (!part?.picture || (editable && el.localName === "table") || isLine(el)) return drawnHere(el, style, box, editable);
  const image = document.createElement("img");
  image.src = part.picture;
  image.alt = "";
  image.draggable = false;
  placePicture(image, box);
  return image;
}

/** A line is always drawn here: it has two ends the editor moves one at a time, which the server's
 * picture of a box cannot follow. */
export const isLine = (el: Element) => el.localName === "x-shape" && el.getAttribute("data-shape") === "line";

/** A shape or table the server has not drawn yet (a layout's preview, an element just added),
 * drawn here as near as the browser can; anything else waits for the server's picture. */
function drawnHere(el: Element, style: Map<string, string>, [x, y, w, h]: Box, editable = false): HTMLElement | null {
  const node = document.createElement(el.localName === "table" ? "table" : "div");
  Object.assign(node.style, { position: "absolute", left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${h}px` });
  if (el.localName === "x-shape") {
    const shape = el.getAttribute("data-shape") ?? "rect";
    if (shape === "line") return lineNode(node, [w, h], style, el.getAttribute("data-direction") === "up");
    applyStyle(node, new Map([...style].filter(([name]) => ["background", "border", "opacity"].includes(name))));
    if (shape === "ellipse") node.style.borderRadius = "50%";
    if (shape === "round-rect") node.style.borderRadius = style.get("border-radius") ?? `${Math.round(Math.min(w, h) * 0.12)}px`;
    if (shape === "triangle" || shape === "arrow") node.style.clipPath = `polygon(${(shape === "triangle" ? trianglePoints(w, h) : arrowPoints(w, h)).map(([px, py]) => `${px}px ${py}px`).join(",")})`;
    return node;
  }
  if (el.localName !== "table") return null;
  Object.assign(node.style, { borderCollapse: "collapse", fontSize: style.get("font-size") ?? "28px", tableLayout: "fixed" });
  applyStyle(node, new Map([...style].filter(([name]) => ["font-family", "color"].includes(name))));
  const widths = Array.from(el.querySelectorAll("col"));
  if (widths.length) {
    const group = node.appendChild(document.createElement("colgroup"));
    for (const col of widths) group.append(Object.assign(document.createElement("col"), { style: `width:${parseStyle(col.getAttribute("style") ?? "").get("width") ?? "auto"}` }));
  }
  for (const row of Array.from(el.querySelectorAll("tr"))) {
    const tr = node.appendChild(document.createElement("tr"));
    for (const cell of Array.from(row.children)) tr.append(drawCell(cell, style, editable));
  }
  return node;
}

/** The corners the compiler gives a triangle and an arrow in a `w` by `h` box. */
const trianglePoints = (w: number, h: number): [number, number][] => [[w / 2, 0], [w, h], [0, h]];
function arrowPoints(w: number, h: number): [number, number][] {
  const head = Math.min(h, w / 2);
  const shaft = h * 0.3;
  return [[0, shaft], [w - head, shaft], [w - head, 0], [w, h / 2], [w - head, h], [w - head, h - shaft], [0, h - shaft]];
}

/** A line between two corners of its box, in the border's colour and width. */
function lineNode(node: HTMLElement, [w, h]: [number, number], style: Map<string, string>, rises: boolean): HTMLElement {
  const border = /^(\d+(?:\.\d+)?)px\s+(\w+)\s+(#\w+)/.exec(style.get("border") ?? "");
  const [width, dash, colour] = border ? [border[1], border[2], border[3]] : ["4", "solid", "#000000"];
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.style.overflow = "visible";
  const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
  line.setAttribute("stroke", colour);
  line.setAttribute("stroke-width", width);
  if (dash === "dashed") line.setAttribute("stroke-dasharray", `${Number(width) * 3} ${Number(width) * 2}`);
  svg.append(line);
  node.append(svg);
  node.dataset.line = "";
  drawLine(node, w, h, rises);
  return node;
}

/** Sets the size of a line node's drawing and which diagonal it runs along. */
function drawLine(node: HTMLElement, w: number, h: number, rises: boolean) {
  const svg = node.querySelector("svg");
  const line = node.querySelector("line");
  if (!svg || !line) return;
  // A flat line's box has one side 0, and the browser draws no svg of zero size, overflow or not.
  svg.setAttribute("width", String(Math.max(w, 1)));
  svg.setAttribute("height", String(Math.max(h, 1)));
  for (const [name, value] of Object.entries({ x1: "0", y1: rises ? String(h) : "0", x2: String(w), y2: rises ? "0" : String(h) })) line.setAttribute(name, value);
  node.dataset.line = rises ? "up" : "down";
}

/** A table cell with its inline formatting; the cell's own colour, fill, weight and alignment. */
function drawCell(cell: Element, table: Map<string, string>, editable: boolean): HTMLElement {
  const td = document.createElement(cell.localName === "th" ? "th" : "td");
  td.append(...Array.from(copyText(cell).childNodes));
  td.style.border = `1px solid ${table.get("border-color") ?? "#CBD2DC"}`;
  td.style.padding = "0.3em 0.5em";
  td.style.textAlign = "left";
  if (cell.localName === "th") td.style.fontWeight = "700";
  applyStyle(td, new Map([...parseStyle(cell.getAttribute("style") ?? "")].filter(([name]) => ["background", "color", "text-align", "font-weight"].includes(name))));
  if (editable) td.contentEditable = "true";
  return td;
}

/** Moves or resizes an element's node while it is dragged; a picture stretches until the
 * server draws it again at its new size. */
export function placeNode(node: HTMLElement, box: Box, rises?: boolean) {
  if (node instanceof HTMLImageElement) return placePicture(node, box);
  const [x, y, w, h] = box;
  Object.assign(node.style, { left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${h}px` });
  if (node.dataset.line !== undefined) drawLine(node, w, h, rises ?? node.dataset.line === "up");
}

function placePicture(image: HTMLImageElement, [x, y, w, h]: Box) {
  const m = PICTURE_MARGIN;
  Object.assign(image.style, { left: `${x - m}px`, top: `${y - m}px`, width: `${w + 2 * m}px`, height: `${h + 2 * m}px` });
}

/** The text element rebuilt from the section's own tags; anything else in it is left out. */
function copyText(el: Element): HTMLElement {
  const node = document.createElement(el.localName);
  for (const child of Array.from(el.childNodes)) {
    if (child.nodeType === Node.TEXT_NODE) node.append(child.textContent ?? "");
    else if (child instanceof Element && INLINE_TAGS.has(child.localName)) {
      const copy = copyText(child);
      if (child.localName === "span") applyStyle(copy, parseStyle(child.getAttribute("style") ?? ""));
      node.append(copy);
    }
  }
  return node;
}

/** Sets each declaration that is a plain value: one that calls a CSS function (`url()`) could
 * fetch from elsewhere, which a section never needs. */
function applyStyle(node: HTMLElement, style: Map<string, string>) {
  for (const [name, value] of style) {
    if (/[()\\]/.test(value)) continue;
    node.style.setProperty(name, value);
  }
}

/** The text node of a drawn text element: what becomes editable. */
export const textNode = (node: HTMLElement | null) => (node?.firstElementChild as HTMLElement | null) ?? null;

const BACK: Record<string, string> = { b: "b", strong: "b", i: "i", em: "i", u: "u", br: "br", span: "span", font: "span" };

/** The edited text written back into the section's element `el`, in the section language's own
 * tags: what the browser adds while typing (`div`s, `font`, styles) is turned into those or left
 * out, and a list keeps one `li` per item. */
export function writeTextBack(edited: HTMLElement, el: Element) {
  el.replaceChildren();
  if (el.localName === "ul" || el.localName === "ol") {
    for (const child of Array.from(edited.childNodes)) {
      const li = el.ownerDocument.createElement("li");
      const holder = document.createElement("span");
      holder.append(child.cloneNode(true));
      copyBack(child instanceof HTMLElement && child.localName === "li" ? child : holder, li);
      if ((li.textContent ?? "").trim()) el.append(li);
    }
    return;
  }
  copyBack(edited, el);
  while (el.lastChild instanceof Element && el.lastChild.localName === "br") el.lastChild.remove();
}

function copyBack(from: Node, to: Element) {
  const doc = to.ownerDocument;
  for (const child of Array.from(from.childNodes)) {
    if (child.nodeType === Node.TEXT_NODE) {
      to.append((child.textContent ?? "").replace(/\u200b/g, ""));
      continue;
    }
    if (!(child instanceof HTMLElement)) continue;
    const tag = BACK[child.localName];
    const colour = hexColour(child.getAttribute("color") ?? child.style.color ?? "");
    if (["div", "p", "li"].includes(child.localName)) {
      const last = to.lastChild;
      if (to.childNodes.length && !(last instanceof Element && last.localName === "br")) to.append(doc.createElement("br"));
      copyBack(child, to);
    } else if (!tag || (tag === "span" && !colour)) {
      copyBack(child, to);
    } else {
      const copy = doc.createElement(tag);
      if (tag === "span") copy.setAttribute("style", `color:${colour}`);
      copyBack(child, copy);
      to.append(copy);
    }
  }
}
