import { STACK, elementsOf, setBox, setStyle, styleOf, type Box } from "./slideSource";

/** Moving elements into, out of and within containers (decision 0018). */

/** A container, and where what it holds is, for finding where a dragged element would land. */
export interface StackSlot {
  /** The container's place among the section's elements. */
  node: number;
  box: Box;
  row: boolean;
  children: Box[];
}

export interface Drop {
  node: number;
  /** Where among the container's other children the element would go. */
  at: number;
  box: Box;
  /** A thin box across the container, where the element would go. */
  line: Box;
}

const FLEX = ["flex-grow", "flex-shrink", "flex-basis"];
/** What a container sizes by its content: text and other containers. */
const FLOWS = new Set(["h1", "h2", "h3", "p", "ul", "ol", STACK]);
const LINE = 4;
const isRow = (stack: Element) => stack.getAttribute("data-layout") === "row";

/** The containers a dragged element could be dropped into, with the boxes of what each holds
 * (the dragged element and what is inside it left out), in document order. */
export function stackSlots(doc: Document, boxes: (Box | null)[], dragged: Element | null): StackSlot[] {
  const els = elementsOf(doc);
  const slots: StackSlot[] = [];
  els.forEach((el, node) => {
    const box = boxes[node];
    if (el.localName !== STACK || !box || (dragged && dragged.contains(el))) return;
    const children = Array.from(el.children)
      .filter((child) => child !== dragged && child.localName !== "aside")
      .map((child) => boxes[els.indexOf(child)])
      .filter((b): b is Box => b !== null && b !== undefined);
    slots.push({ node, box, row: isRow(el), children });
  });
  return slots;
}

/** Where a point on the slide would drop an element: into the innermost container that holds it,
 * before the children whose middle is beyond the point. */
export function dropTarget(slots: StackSlot[], x: number, y: number): Drop | null {
  const within = slots.filter(({ box: [bx, by, bw, bh] }) => x >= bx && x <= bx + bw && y >= by && y <= by + bh);
  const slot = within[within.length - 1];
  if (!slot) return null;
  const { box, row, children } = slot;
  const along = row ? x : y;
  const middle = (b: Box) => (row ? b[0] + b[2] / 2 : b[1] + b[3] / 2);
  const at = children.filter((child) => middle(child) < along).length;
  const edge = (b: Box, end: boolean) => (row ? b[0] + (end ? b[2] : 0) : b[1] + (end ? b[3] : 0));
  let where: number;
  if (!children.length) where = row ? box[0] + box[2] / 2 : box[1] + box[3] / 2;
  else if (at === 0) where = edge(children[0], false) - 6;
  else if (at === children.length) where = edge(children[at - 1], true) + 6;
  else where = (edge(children[at - 1], true) + edge(children[at], false)) / 2;
  const line: Box = row ? [where - LINE / 2, box[1] + 8, LINE, box[3] - 16] : [box[0] + 8, where - LINE / 2, box[2] - 16, LINE];
  return { node: slot.node, at, box, line };
}

/** `node` as the `at`th child of `stack`. Its own place on the slide (or its size along another
 * direction) goes, and text takes the room the container gives it. */
export function moveInto(node: Element, stack: Element, at: number) {
  const row = isRow(stack);
  const from = node.parentElement;
  const fromRow = from?.localName === STACK ? isRow(from) : null;
  if (fromRow !== row) {
    for (const name of ["left", "top", ...FLEX]) setStyle(node, name, null);
    if (FLOWS.has(node.localName)) {
      setStyle(node, "height", null);
      if (!row) setStyle(node, "width", null);
    }
  }
  if (row && FLOWS.has(node.localName) && !styleOf(node, "width") && !styleOf(node, "flex-grow")) setStyle(node, "flex-grow", "1");
  const others = Array.from(stack.children).filter((child) => child !== node && child.localName !== "aside");
  stack.insertBefore(node, others[at] ?? null);
}

/** `node`, out of its container, onto the slide at `box`, above everything else. */
export function moveOut(node: Element, box: Box) {
  const section = node.ownerDocument.documentElement;
  for (const name of FLEX) setStyle(node, name, null);
  section.append(node);
  setBox(node, box);
}

