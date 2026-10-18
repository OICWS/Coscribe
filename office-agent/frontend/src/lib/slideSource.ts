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

/** The section's elements in order, as the server numbers its parts: all but the notes. */
export const elementsOf = (doc: Document) => Array.from(doc.documentElement.children).filter((el) => el.localName !== "aside");

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
