import { useEffect, useRef } from "react";
import { elementsOf } from "../../lib/slideSource";
import { tableRows } from "../../lib/slideTable";
import { writeTextBack } from "./sectionDom";

type Change = (edit: (elements: Element[]) => void, redraw: boolean) => void;

const cellsOf = (row: Element) => Array.from(row.children) as HTMLElement[];

/** Typing into a table's cells in place: the table is drawn here with typeable cells (instead of
 * the server's picture of it) from a double-click or Enter; Tab and Shift+Tab move between cells.
 * The typing ends on Escape or a press away from the table, and the cells' text is written back
 * into the section's table and saved. */
export function useTableEditing(
  doc: Document | null,
  nodes: { current: (HTMLElement | null)[] },
  change: Change,
  /** The table being typed into, held by the editor because it decides how the slide is drawn. */
  [editing, setEditing]: [number | null, (at: number | null) => void],
) {
  const editingRef = useRef<number | null>(null);
  // Where to put the caret once the table has been drawn with typeable cells.
  const first = useRef<{ x: number; y: number } | null | undefined>(undefined);

  const stop = () => {
    const at = editingRef.current;
    editingRef.current = null;
    setEditing(null);
    const node = at === null ? null : nodes.current[at];
    if (at === null || !node || !doc) return;
    const el = elementsOf(doc)[at];
    const probe = el.cloneNode(true) as Element;
    writeCells(node, probe);
    if (probe.innerHTML !== el.innerHTML) change((els) => writeCells(node, els[at]), true);
  };

  const start = (at: number, point?: { x: number; y: number }) => {
    editingRef.current = at;
    first.current = point ?? null;
    setEditing(at);
  };

  // Once the typeable table is drawn, the caret goes to the cell that was clicked, or the first.
  useEffect(() => {
    if (editing === null || first.current === undefined) return;
    const node = nodes.current[editing];
    const point = first.current;
    first.current = undefined;
    const cells = node ? Array.from(node.querySelectorAll("td,th")) as HTMLElement[] : [];
    const target = (point && cellAtPoint(node, point)) || cells[0];
    target?.focus();
    if (target) selectContents(target);
  });

  useEffect(() => {
    if (editing === null) return;
    const onDown = (e: PointerEvent) => {
      const path = e.composedPath();
      if (nodes.current[editing] && path.includes(nodes.current[editing]!)) return;
      if (path.some((n) => n instanceof HTMLElement && (n.dataset.formatBar !== undefined || n.closest("[role=dialog],[role=menu]")))) return;
      stop();
    };
    window.addEventListener("pointerdown", onDown, true);
    return () => window.removeEventListener("pointerdown", onDown, true);
  });

  const onKey = (e: React.KeyboardEvent) => {
    const at = editingRef.current;
    if (at === null) return;
    e.stopPropagation();
    if (e.key === "Escape") {
      e.preventDefault();
      stop();
    } else if (e.key === "Tab") {
      e.preventDefault();
      moveBy(nodes.current[at], e.shiftKey ? -1 : 1);
    } else if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      document.execCommand("insertLineBreak");
    }
  };

  const onPaste = (e: React.ClipboardEvent) => {
    if (editingRef.current === null) return;
    e.preventDefault();
    document.execCommand("insertText", false, e.clipboardData.getData("text/plain"));
  };

  return { editing, start, stop, onKey, onPaste };
}

/** The cells' text, written back into the section's table in the section language's own tags. */
function writeCells(node: HTMLElement, table: Element) {
  const drawn = Array.from(node.querySelectorAll("tr"));
  tableRows(table).forEach((row, r) => {
    const cells = Array.from(row.children);
    cells.forEach((cell, c) => {
      const edited = cellsOf(drawn[r])[c];
      if (edited) writeTextBack(edited, cell);
    });
  });
}

function moveBy(node: HTMLElement | null, step: number) {
  const cells = Array.from(node?.querySelectorAll("td,th") ?? []) as HTMLElement[];
  const here = cells.findIndex((c) => c.getRootNode() instanceof ShadowRoot && (c.getRootNode() as ShadowRoot).activeElement === c);
  const next = cells[here + step];
  if (!next) return;
  next.focus();
  selectContents(next);
}

function selectContents(cell: HTMLElement) {
  const root = cell.getRootNode() as ShadowRoot & { getSelection?: () => Selection | null };
  const selection = root.getSelection?.() ?? window.getSelection();
  const range = document.createRange();
  range.selectNodeContents(cell);
  selection?.removeAllRanges();
  selection?.addRange(range);
}

/** The cell under a screen point, if the point is inside the table. */
function cellAtPoint(node: HTMLElement | null, { x, y }: { x: number; y: number }): HTMLElement | null {
  const cells = Array.from(node?.querySelectorAll("td,th") ?? []) as HTMLElement[];
  return cells.find((c) => {
    const r = c.getBoundingClientRect();
    return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
  }) ?? null;
}
