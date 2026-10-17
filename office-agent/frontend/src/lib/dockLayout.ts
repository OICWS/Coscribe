/** The panels in one column of the window (dockArrangement.ts): a tree of
 * splits, each a row or a column of children with their shares of its
 * length. Pure functions only. */

export type PanelId = "task" | "browser" | "background" | "viewer";
export const PANEL_IDS: readonly PanelId[] = ["task", "browser", "background", "viewer"];

export type Direction = "row" | "col";
export type Edge = "left" | "right" | "top" | "bottom";

export type DockNode =
  | { kind: "panel"; id: PanelId }
  | { kind: "split"; dir: Direction; children: DockNode[]; sizes: number[] };

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** The gap between a split's children: what a resize gutter is dragged by. */
export interface Gutter {
  /** Child indexes from the root down to the split. */
  path: number[];
  /** The gutter sits before child `index`. */
  index: number;
  dir: Direction;
  rect: Rect;
  /** The split's length minus its gaps, in pixels. */
  length: number;
}

export interface Layout {
  panels: Partial<Record<PanelId, Rect>>;
  gutters: Gutter[];
}

export const GAP = 8;

const edgeDirection = (edge: Edge): Direction => (edge === "left" || edge === "right" ? "row" : "col");
const before = (edge: Edge) => edge === "left" || edge === "top";

export function panelIds(node: DockNode | null): PanelId[] {
  if (!node) return [];
  if (node.kind === "panel") return [node.id];
  return node.children.flatMap(panelIds);
}

/** Drops empty splits, lifts a split's only child, merges a child split
 * running the same way into its parent, and makes shares sum to 1. */
export function tidy(node: DockNode | null): DockNode | null {
  if (!node || node.kind === "panel") return node;
  const children: DockNode[] = [];
  const sizes: number[] = [];
  node.children.forEach((raw, i) => {
    const child = tidy(raw);
    if (!child) return;
    const share = node.sizes[i] ?? 0;
    if (child.kind === "split" && child.dir === node.dir) {
      child.children.forEach((grandchild, j) => {
        children.push(grandchild);
        sizes.push(share * child.sizes[j]);
      });
    } else {
      children.push(child);
      sizes.push(share);
    }
  });
  if (children.length === 0) return null;
  if (children.length === 1) return children[0];
  const total = sizes.reduce((a, b) => a + b, 0);
  return {
    kind: "split",
    dir: node.dir,
    children,
    sizes: total > 0 ? sizes.map((s) => s / total) : sizes.map(() => 1 / sizes.length),
  };
}

/** The tree with only `visible` panels, the others' room given to their siblings. */
export function prune(node: DockNode | null, visible: readonly PanelId[]): DockNode | null {
  if (!node) return null;
  if (node.kind === "panel") return visible.includes(node.id) ? node : null;
  const kept = node.children.map((child) => prune(child, visible));
  return tidy({
    kind: "split",
    dir: node.dir,
    children: kept.filter((c): c is DockNode => c !== null),
    sizes: node.sizes.filter((_, i) => kept[i] !== null),
  });
}

export function removePanel(node: DockNode | null, id: PanelId): DockNode | null {
  return prune(
    node,
    panelIds(node).filter((other) => other !== id),
  );
}

/** Puts `id` beside `target` on its `edge`, or with `target` null, along
 * that edge of everything. A panel already in the tree is moved. */
export function insertPanel(node: DockNode | null, id: PanelId, target: PanelId | null, edge: Edge): DockNode {
  const leaf: DockNode = { kind: "panel", id };
  const root = removePanel(node, id);
  if (!root) return leaf;
  const dir = edgeDirection(edge);
  if (target === null || !panelIds(root).includes(target)) {
    if (root.kind === "split" && root.dir === dir) {
      const share = 1 / (root.children.length + 1);
      const sizes = root.sizes.map((s) => s * (1 - share));
      return before(edge)
        ? { ...root, children: [leaf, ...root.children], sizes: [share, ...sizes] }
        : { ...root, children: [...root.children, leaf], sizes: [...sizes, share] };
    }
    return {
      kind: "split",
      dir,
      children: before(edge) ? [leaf, root] : [root, leaf],
      sizes: before(edge) ? [0.4, 0.6] : [0.6, 0.4],
    };
  }
  const place = (n: DockNode): DockNode => {
    if (n.kind === "panel") {
      if (n.id !== target) return n;
      return { kind: "split", dir, children: before(edge) ? [leaf, n] : [n, leaf], sizes: [0.5, 0.5] };
    }
    const at = n.children.findIndex((c) => c.kind === "panel" && c.id === target);
    if (at >= 0 && n.dir === dir) {
      const half = n.sizes[at] / 2;
      const children = [...n.children];
      const sizes = [...n.sizes];
      sizes[at] = half;
      const where = before(edge) ? at : at + 1;
      children.splice(where, 0, leaf);
      sizes.splice(where, 0, half);
      return { ...n, children, sizes };
    }
    return { ...n, children: n.children.map(place) };
  };
  return tidy(place(root)) ?? leaf;
}

/** The tree with the shares of the split at `path` replaced. */
export function withSizes(node: DockNode, path: number[], sizes: number[]): DockNode {
  if (node.kind === "panel") return node;
  if (path.length === 0) return { ...node, sizes };
  const [head, ...rest] = path;
  return { ...node, children: node.children.map((c, i) => (i === head ? withSizes(c, rest, sizes) : c)) };
}

export function nodeAt(node: DockNode, path: number[]): DockNode {
  return path.reduce((n, i) => (n.kind === "split" ? n.children[i] : n), node);
}

/** New shares for the two children either side of a gutter dragged by
 * `delta` pixels, each kept at least `min` pixels long. */
export function dragGutter(sizes: number[], index: number, delta: number, length: number, min: number): number[] {
  const a = sizes[index - 1] * length;
  const b = sizes[index] * length;
  const lo = Math.min(0, min - a);
  const hi = Math.max(0, b - min);
  const d = Math.max(lo, Math.min(hi, delta));
  const next = [...sizes];
  next[index - 1] = (a + d) / length;
  next[index] = (b - d) / length;
  return next;
}

/** Pixel boxes for every panel and gutter inside `area`. */
export function layout(node: DockNode | null, area: Rect, gap = GAP): Layout {
  const result: Layout = { panels: {}, gutters: [] };
  const walk = (n: DockNode, r: Rect, path: number[]) => {
    if (n.kind === "panel") {
      result.panels[n.id] = r;
      return;
    }
    const horizontal = n.dir === "row";
    const total = horizontal ? r.w : r.h;
    const length = Math.max(0, total - gap * (n.children.length - 1));
    let cumulative = 0;
    let start = horizontal ? r.x : r.y;
    n.children.forEach((child, i) => {
      cumulative += n.sizes[i];
      const end = Math.round((horizontal ? r.x : r.y) + cumulative * length + i * gap);
      const size = Math.max(0, end - start);
      if (i > 0) {
        const g = start - gap;
        result.gutters.push({
          path,
          index: i,
          dir: n.dir,
          length,
          rect: horizontal ? { x: g, y: r.y, w: gap, h: r.h } : { x: r.x, y: g, w: r.w, h: gap },
        });
      }
      walk(child, horizontal ? { x: start, y: r.y, w: size, h: r.h } : { x: r.x, y: start, w: r.w, h: size }, [
        ...path,
        i,
      ]);
      start = end + gap;
    });
  };
  if (node) walk(node, area, []);
  return result;
}

export function isDockNode(value: unknown): value is DockNode {
  if (!value || typeof value !== "object") return false;
  const n = value as Record<string, unknown>;
  if (n.kind === "panel") return PANEL_IDS.includes(n.id as PanelId);
  return (
    n.kind === "split" &&
    (n.dir === "row" || n.dir === "col") &&
    Array.isArray(n.children) &&
    Array.isArray(n.sizes) &&
    n.children.length === n.sizes.length &&
    n.sizes.every((s) => typeof s === "number" && s >= 0) &&
    n.children.every(isDockNode)
  );
}

export interface PlaceHint {
  target: PanelId;
  edge: Edge;
}

/** Where `id` sits relative to a neighbour, so it can go back there after
 * being closed: after the sibling before it, else before the one after. */
export function neighbourOf(node: DockNode | null, id: PanelId): PlaceHint | null {
  const find = (n: DockNode): PlaceHint | null => {
    if (n.kind === "panel") return null;
    const at = n.children.findIndex((c) => c.kind === "panel" && c.id === id);
    if (at >= 0) {
      if (at > 0) {
        const ids = panelIds(n.children[at - 1]);
        return { target: ids[ids.length - 1], edge: n.dir === "row" ? "right" : "bottom" };
      }
      if (n.children.length > 1) {
        return { target: panelIds(n.children[1])[0], edge: n.dir === "row" ? "left" : "top" };
      }
      return null;
    }
    for (const child of n.children) {
      const hint = find(child);
      if (hint) return hint;
    }
    return null;
  };
  return node ? find(node) : null;
}
