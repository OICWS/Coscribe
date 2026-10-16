/** The whole window's arrangement: columns of side panels on either side of
 * the conversation, which takes the width they leave. Each column holds a
 * split tree of panels (dockLayout.ts) and keeps its own width in pixels,
 * so resizing the window changes the conversation, not the panels. */

import {
  GAP,
  insertPanel,
  isDockNode,
  layout,
  neighbourOf,
  panelIds,
  removePanel,
  type DockNode,
  type Edge,
  type Gutter,
  type PanelId,
  type Rect,
} from "./dockLayout";

export type Side = "left" | "right";

export interface Column {
  tree: DockNode;
  width: number;
}

/** Columns in screen order, left to right, on each side. */
export interface Arrangement {
  left: Column[];
  right: Column[];
}

export const EMPTY: Arrangement = { left: [], right: [] };
export const COLUMN_MIN = 280;

export interface ColumnRef {
  side: Side;
  index: number;
}

export type Hint = { target: PanelId; edge: Edge } | { side: Side; index: number; width: number };

export interface ArrangementLayout {
  chat: Rect;
  panels: Partial<Record<PanelId, Rect>>;
  /** Gaps inside a column, between its panels. */
  gutters: (Gutter & { column: ColumnRef })[];
  /** Gaps that resize a whole column. */
  columnGutters: { column: ColumnRef; rect: Rect }[];
  /** No room for the conversation beside the panels: they lie over it. */
  overlay: boolean;
}

export function arrangementPanels(arr: Arrangement): PanelId[] {
  return [...arr.left, ...arr.right].flatMap((c) => panelIds(c.tree));
}

export function columnOf(arr: Arrangement, id: PanelId): ColumnRef | null {
  for (const side of ["left", "right"] as const) {
    const index = arr[side].findIndex((c) => panelIds(c.tree).includes(id));
    if (index >= 0) return { side, index };
  }
  return null;
}

function mapColumn(arr: Arrangement, ref: ColumnRef, change: (c: Column) => Column | null): Arrangement {
  const columns = arr[ref.side]
    .map((c, i) => (i === ref.index ? change(c) : c))
    .filter((c): c is Column => c !== null);
  return { ...arr, [ref.side]: columns };
}

export function withoutPanel(arr: Arrangement, id: PanelId): Arrangement {
  const ref = columnOf(arr, id);
  if (!ref) return arr;
  return mapColumn(arr, ref, (c) => {
    const tree = removePanel(c.tree, id);
    return tree ? { ...c, tree } : null;
  });
}

export function addColumn(arr: Arrangement, side: Side, index: number, column: Column): Arrangement {
  const columns = [...arr[side]];
  columns.splice(Math.max(0, Math.min(index, columns.length)), 0, column);
  return { ...arr, [side]: columns };
}

export function withColumnTree(arr: Arrangement, ref: ColumnRef, tree: DockNode): Arrangement {
  return mapColumn(arr, ref, (c) => ({ ...c, tree }));
}

export function withColumnWidth(arr: Arrangement, ref: ColumnRef, width: number): Arrangement {
  return mapColumn(arr, ref, (c) => ({ ...c, width: Math.round(width) }));
}

/** Pixel boxes for the conversation, every panel and every gap. Columns
 * give up width down to COLUMN_MIN before the conversation goes below
 * `chatMin`; past that the panels lie over the conversation. */
export function arrangementLayout(arr: Arrangement, area: Rect, chatMin: number): ArrangementLayout {
  const all: { column: Column; ref: ColumnRef }[] = [
    ...arr.left.map((column, index) => ({ column, ref: { side: "left" as const, index } })),
    ...arr.right.map((column, index) => ({ column, ref: { side: "right" as const, index } })),
  ];
  const result: ArrangementLayout = { chat: area, panels: {}, gutters: [], columnGutters: [], overlay: false };
  if (all.length === 0) return result;

  const margins = (arr.left.length ? GAP : 0) + (arr.right.length ? GAP : 0);
  const gaps = all.length * GAP;
  const wanted = all.reduce((sum, { column }) => sum + column.width, 0);
  let widths = all.map(({ column }) => column.width);
  const room = area.w - margins - gaps - chatMin;
  if (wanted > room) {
    const spare = wanted - all.length * COLUMN_MIN;
    const cut = Math.min(wanted - room, Math.max(0, spare));
    widths = widths.map((w) => (spare > 0 ? w - ((w - COLUMN_MIN) / spare) * cut : COLUMN_MIN));
    result.overlay = wanted - cut > room;
  }
  widths = widths.map((w) => Math.max(COLUMN_MIN, Math.round(w)));

  const top = area.y + GAP;
  const height = area.h - 2 * GAP;
  const leftCount = arr.left.length;
  const place = (i: number, x: number) => {
    const { column, ref } = all[i];
    const rect = { x, y: top, w: widths[i], h: height };
    const inner = layout(column.tree, rect);
    Object.assign(result.panels, inner.panels);
    for (const g of inner.gutters) result.gutters.push({ ...g, column: ref });
    return rect;
  };

  let x = area.x + (leftCount ? GAP : 0);
  for (let i = 0; i < leftCount; i++) {
    const rect = place(i, x);
    result.columnGutters.push({ column: all[i].ref, rect: { x: rect.x + rect.w, y: area.y, w: GAP, h: area.h } });
    x += rect.w + GAP;
  }
  let end = area.x + area.w - (arr.right.length ? GAP : 0);
  for (let i = all.length - 1; i >= leftCount; i--) {
    const rect = place(i, end - widths[i]);
    result.columnGutters.push({ column: all[i].ref, rect: { x: rect.x - GAP, y: area.y, w: GAP, h: area.h } });
    end = rect.x - GAP;
  }
  result.chat = result.overlay ? area : { x, y: area.y, w: Math.max(0, end - x), h: area.h };
  if (result.overlay) result.columnGutters = [];
  return result;
}

export type Drop = { kind: "beside"; target: PanelId; edge: Edge } | { kind: "column"; side: Side; index: number };

const OUTER_EDGE = 28;

/** Where a dragged panel would go with the pointer at (x, y): beside the
 * panel under it, on that panel's nearest edge; on either side of the
 * conversation; or in a new outermost column near the window's edge. */
export function dropAt(placed: ArrangementLayout, arr: Arrangement, area: Rect, dragged: PanelId, x: number, y: number): Drop | null {
  if (x < area.x || x > area.x + area.w || y < area.y || y > area.y + area.h) return null;
  if (x < area.x + OUTER_EDGE) return { kind: "column", side: "left", index: 0 };
  if (x > area.x + area.w - OUTER_EDGE) return { kind: "column", side: "right", index: arr.right.length };
  for (const id of Object.keys(placed.panels) as PanelId[]) {
    const r = placed.panels[id];
    if (id === dragged || !r || x < r.x || x > r.x + r.w || y < r.y || y > r.y + r.h) continue;
    const distances: Record<Edge, number> = {
      left: (x - r.x) / r.w,
      right: (r.x + r.w - x) / r.w,
      top: (y - r.y) / r.h,
      bottom: (r.y + r.h - y) / r.h,
    };
    const edge = (Object.keys(distances) as Edge[]).reduce((a, b) => (distances[a] <= distances[b] ? a : b));
    return { kind: "beside", target: id, edge };
  }
  const chat = placed.chat;
  if (!placed.overlay && x >= chat.x && x <= chat.x + chat.w) {
    return x < chat.x + chat.w / 2
      ? { kind: "column", side: "left", index: arr.left.length }
      : { kind: "column", side: "right", index: 0 };
  }
  return null;
}

/** The arrangement with `id` taken from wherever it is and put at `drop`;
 * a new column gets `width`. */
export function applyDrop(arr: Arrangement, id: PanelId, drop: Drop, width: number): Arrangement {
  const from = columnOf(arr, id);
  let next = withoutPanel(arr, id);
  const leaf: DockNode = { kind: "panel", id };
  if (drop.kind === "beside") {
    const ref = columnOf(next, drop.target);
    if (!ref) return arr;
    return withColumnTree(next, ref, insertPanel(next[ref.side][ref.index].tree, id, drop.target, drop.edge));
  }
  let index = drop.index;
  // The panel's own column, if it held only this panel, is gone now.
  if (from && from.side === drop.side && from.index < index && next[from.side].length < arr[from.side].length) index -= 1;
  next = addColumn(next, drop.side, index, { tree: leaf, width });
  return next;
}

/** The Move menu: left and right make an outermost column; top and bottom
 * stack the panel along that edge of its own column, or of the nearest
 * other column when it is alone in its own. */
export function movePanel(arr: Arrangement, id: PanelId, edge: Edge, width: number): Arrangement {
  if (edge === "left") return applyDrop(arr, id, { kind: "column", side: "left", index: 0 }, width);
  if (edge === "right") return applyDrop(arr, id, { kind: "column", side: "right", index: arr.right.length }, width);
  const ref = columnOf(arr, id);
  if (!ref) return arr;
  const own = arr[ref.side][ref.index];
  if (panelIds(own.tree).length > 1) {
    return withColumnTree(arr, ref, insertPanel(own.tree, id, null, edge));
  }
  const rest = withoutPanel(arr, id);
  const target =
    ref.side === "right" ? (rest.right[0] ?? rest.left[rest.left.length - 1]) : (rest.left[rest.left.length - 1] ?? rest.right[0]);
  if (!target) return arr;
  const targetRef = columnOf(rest, panelIds(target.tree)[0]);
  return targetRef ? withColumnTree(rest, targetRef, insertPanel(target.tree, id, null, edge)) : arr;
}

/** Every panel side by side in its own column on the right, or all in one column. */
export function arrangeAll(arr: Arrangement, dir: "row" | "col"): Arrangement {
  const ids = arrangementPanels(arr);
  const total = [...arr.left, ...arr.right].reduce((sum, c) => sum + c.width, 0);
  if (ids.length < 2) return arr;
  if (dir === "row") {
    return { left: [], right: ids.map((id) => ({ tree: { kind: "panel", id }, width: Math.round(total / ids.length) })) };
  }
  return {
    left: [],
    right: [
      {
        tree: { kind: "split", dir: "col", children: ids.map((id) => ({ kind: "panel", id })), sizes: ids.map(() => 1 / ids.length) },
        width: Math.max(...[...arr.left, ...arr.right].map((c) => c.width)),
      },
    ],
  };
}

/** Where `id` sits, to put it back there after it is closed. */
export function hintFor(arr: Arrangement, id: PanelId): Hint | null {
  const ref = columnOf(arr, id);
  if (!ref) return null;
  const column = arr[ref.side][ref.index];
  return neighbourOf(column.tree, id) ?? { side: ref.side, index: ref.index, width: column.width };
}

/** Puts `id` back by its hint, or as a new panel: a column at the right end
 * while the conversation keeps `roomy`, else under the rightmost panel. */
export function openPanel(arr: Arrangement, id: PanelId, hint: Hint | undefined, width: number, room: number): Arrangement {
  if (hint && "target" in hint && arrangementPanels(arr).includes(hint.target)) {
    const ref = columnOf(arr, hint.target);
    if (ref) return withColumnTree(arr, ref, insertPanel(arr[ref.side][ref.index].tree, id, hint.target, hint.edge));
  }
  if (hint && "side" in hint) return addColumn(arr, hint.side, hint.index, { tree: { kind: "panel", id }, width: hint.width });
  const last = arr.right[arr.right.length - 1] ?? arr.left[arr.left.length - 1];
  if (!last || room >= width) return addColumn(arr, "right", arr.right.length, { tree: { kind: "panel", id }, width });
  const ids = panelIds(last.tree);
  const ref = columnOf(arr, ids[0]);
  return ref ? withColumnTree(arr, ref, insertPanel(last.tree, id, ids[ids.length - 1], "bottom")) : arr;
}

export function isArrangement(value: unknown): value is Arrangement {
  if (!value || typeof value !== "object") return false;
  const { left, right } = value as Record<string, unknown>;
  const columns = (list: unknown) =>
    Array.isArray(list) &&
    list.every((c) => c && typeof c === "object" && isDockNode((c as Column).tree) && typeof (c as Column).width === "number" && (c as Column).width > 0);
  return columns(left) && columns(right);
}
