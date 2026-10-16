import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import {
  arrange,
  columnCount,
  dragGutter,
  dropTarget,
  edgeOf,
  insertPanel,
  neighbourOf,
  layout,
  nodeAt,
  PANEL_IDS,
  panelIds,
  placeNewPanel,
  removePanel,
  withSizes,
  type Direction,
  type DockNode,
  type DropTarget,
  type Edge,
  type Gutter,
  type PanelId,
  type Rect,
} from "../../lib/dockLayout";
import { useDockLayout, type DockState } from "../../lib/useDockLayout";
import { DockControls, type DockActions } from "./DockControls";
import { DockPanelContext, type DockPanelApi } from "./dockContext";

/** What the conversation keeps, at least, beside the panels; opening a
 * panel widens the panels only while it keeps CHAT_ROOMY. */
const CHAT_MIN = 380;
const CHAT_ROOMY = 560;
const DOCK_MIN = 300;
const COLUMN_MIN = 300;
const PANEL_MIN = 140;
const PREFERRED_WIDTH: Record<PanelId, number> = { task: 320, browser: 440, background: 440 };
const DRAG_THRESHOLD = 5;

const INTERACTIVE = 'button, a, input, textarea, select, [role="tab"], [role="menuitem"], [contenteditable="true"]';

/** Brings the arrangement in line with the panels this conversation shows.
 * A closed panel leaves a hint to come back beside the same neighbour; with
 * none open the arrangement is kept as it is, for the next one. A new
 * column widens the panels' share of the window while the conversation
 * keeps CHAT_ROOMY; losing one narrows it. */
function sync(prev: DockState, visible: readonly PanelId[], rowWidth: number): DockState {
  if (visible.length === 0) return prev;
  let tree = prev.tree;
  const hints = { ...prev.hints };
  const before = columnCount(tree);
  for (const id of panelIds(tree)) {
    if (visible.includes(id)) continue;
    const hint = neighbourOf(tree, id);
    if (hint) hints[id] = hint;
    tree = removePanel(tree, id);
  }
  let width = tree ? prev.width : 0;
  for (const id of visible) {
    if (panelIds(tree).includes(id)) continue;
    if (!tree) {
      tree = { kind: "panel", id };
      width = PREFERRED_WIDTH[id];
      continue;
    }
    const hint = hints[id];
    const columns = columnCount(tree);
    if (hint && panelIds(tree).includes(hint.target)) {
      tree = insertPanel(tree, id, hint.target, hint.edge);
      if (columnCount(tree) > columns) width += Math.max(0, Math.min(rowWidth - CHAT_ROOMY - width, PREFERRED_WIDTH[id]));
      continue;
    }
    const room = Math.max(0, rowWidth - CHAT_ROOMY - width);
    const grown = width + Math.min(room, PREFERRED_WIDTH[id]);
    tree = placeNewPanel(tree, tree, id, grown, COLUMN_MIN);
    if (columnCount(tree) > columns) {
      tree = keepColumnWidths(tree, width, grown);
      width = grown;
    }
  }
  const after = columnCount(tree);
  if (before > 0 && after > 0 && after < before) width = Math.max(DOCK_MIN, (width * after) / before);
  if (tree === prev.tree && width === prev.width) return prev;
  return { tree, width: Math.round(width), hints };
}

/** After a column is added on the right and the panels widened from
 * `before` to `after` pixels, the old columns keep their widths. */
function keepColumnWidths(tree: DockNode, before: number, after: number): DockNode {
  if (tree.kind !== "split" || tree.dir !== "row") return tree;
  const n = tree.sizes.length;
  const kept = after > before ? before / after : (n - 1) / n;
  return { ...tree, sizes: [...tree.sizes.slice(0, -1).map((s) => (s / (1 - tree.sizes[n - 1])) * kept), 1 - kept] };
}

interface Drag {
  id: PanelId;
  startX: number;
  startY: number;
  dx: number;
  dy: number;
  live: boolean;
  drop: DropTarget | null;
}

/** The side panels beside the conversation, in rows and columns: drag a
 * header to move a panel, drag a gap to resize, and the expand button's
 * menu to move, fill or arrange. Panels are one flat list placed by
 * position, so moving one never remounts it (the browser keeps its tabs). */
export function PanelDock({
  visible,
  titles,
  render,
  onClose,
  leftInset,
}: {
  visible: readonly PanelId[];
  titles: Record<PanelId, string>;
  render: (id: PanelId) => ReactNode;
  onClose: (id: PanelId) => void;
  /** Where the overlay starts when the panels cover the conversation. */
  leftInset: number;
}) {
  const [dock, setDock] = useDockLayout();
  const [filled, setFilled] = useState<PanelId | null>(null);
  const [drag, setDrag] = useState<Drag | null>(null);
  const [menuFor, setMenuFor] = useState<PanelId | null>(null);
  const [rowWidth, setRowWidth] = useState(0);
  const [area, setArea] = useState({ w: 0, h: 0 });
  const rootRef = useRef<HTMLDivElement>(null);
  const areaRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<Drag | null>(null);
  const shown = useMemo(() => PANEL_IDS.filter((id) => visible.includes(id)), [visible]);
  const visibleKey = visible.join(",");

  useEffect(() => {
    const row = rootRef.current?.parentElement;
    if (!row) return;
    const observer = new ResizeObserver(() => setRowWidth(row.clientWidth));
    observer.observe(row);
    setRowWidth(row.clientWidth);
    return () => observer.disconnect();
  }, []);

  useLayoutEffect(() => {
    if (rowWidth <= 0) return;
    setDock((prev) => sync(prev, visibleKey ? (visibleKey.split(",") as PanelId[]) : [], rowWidth));
  }, [visibleKey, rowWidth, setDock]);

  useEffect(() => {
    if (filled && !visible.includes(filled)) setFilled(null);
  }, [filled, visible]);

  const hasPanels = shown.length > 0 && dock.tree !== null;
  const narrow = rowWidth > 0 && rowWidth - CHAT_MIN < DOCK_MIN;
  const overlay = hasPanels && (narrow || filled !== null);
  const width = Math.max(DOCK_MIN, Math.min(dock.width || DOCK_MIN, rowWidth - CHAT_MIN));

  useLayoutEffect(() => {
    const el = areaRef.current;
    if (!el) return;
    const measure = () => setArea({ w: el.clientWidth, h: el.clientHeight });
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    measure();
    return () => observer.disconnect();
  }, [hasPanels]);

  const areaRect: Rect = { x: 0, y: 0, w: area.w, h: area.h };
  const placed = layout(dock.tree, areaRect);
  const rects = filled ? { [filled]: areaRect } : placed.panels;

  const setTree = useCallback(
    (update: (tree: DockState["tree"]) => DockState["tree"]) => setDock((prev) => ({ ...prev, tree: update(prev.tree) })),
    [setDock],
  );
  const setMenuOpen = useCallback(
    (id: PanelId, open: boolean) => setMenuFor((current) => (open ? id : current === id ? null : current)),
    [],
  );

  const actions: DockActions = {
    filled,
    panelCount: shown.length,
    edgeOf: (id) => (filled ? null : edgeOf(placed.panels, areaRect, id)),
    move: (id, edge: Edge) => {
      setFilled(null);
      setTree((tree) => insertPanel(tree, id, null, edge));
    },
    fill: setFilled,
    arrange: (dir: Direction) => {
      setFilled(null);
      setTree((tree) => arrange(tree, dir));
    },
    close: onClose,
    setMenuOpen,
  };

  // Escape puts a dragged panel back, then leaves the filled window.
  useEffect(() => {
    if (!drag?.live && !filled) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || menuFor) return;
      if (dragRef.current?.live) {
        dragRef.current = null;
        setDrag(null);
      } else setFilled(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drag?.live, filled, menuFor]);

  const startDrag = (id: PanelId, e: ReactPointerEvent<HTMLElement>) => {
    if (e.button !== 0 || filled || shown.length < 2) return;
    if ((e.target as HTMLElement).closest(INTERACTIVE)) return;
    const start: Drag = { id, startX: e.clientX, startY: e.clientY, dx: 0, dy: 0, live: false, drop: null };
    dragRef.current = start;
    const onMove = (ev: PointerEvent) => {
      const current = dragRef.current;
      if (!current) return;
      const dx = ev.clientX - current.startX;
      const dy = ev.clientY - current.startY;
      if (!current.live && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
      if (!current.live) document.body.style.userSelect = "none";
      const box = areaRef.current?.getBoundingClientRect();
      const drop = box ? dropTarget(placed.panels, areaRect, current.id, ev.clientX - box.left, ev.clientY - box.top) : null;
      const next = { ...current, dx, dy, live: true, drop };
      dragRef.current = next;
      setDrag(next);
    };
    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
      document.body.style.removeProperty("user-select");
      const done = dragRef.current;
      dragRef.current = null;
      setDrag(null);
      if (done?.live && done.drop) {
        const { target, edge } = done.drop;
        setTree((tree) => insertPanel(tree, done.id, target, edge));
      }
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
  };

  const startGutter = (gutter: Gutter, e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.button !== 0 || !dock.tree) return;
    e.preventDefault();
    const handle = e.currentTarget;
    handle.setPointerCapture(e.pointerId);
    const split = nodeAt(dock.tree, gutter.path);
    if (split.kind !== "split") return;
    const sizes = split.sizes;
    const from = gutter.dir === "row" ? e.clientX : e.clientY;
    const min = gutter.dir === "row" ? COLUMN_MIN * 0.75 : PANEL_MIN;
    const onMove = (ev: PointerEvent) => {
      const delta = (gutter.dir === "row" ? ev.clientX : ev.clientY) - from;
      const next = dragGutter(sizes, gutter.index, delta, gutter.length, min);
      setTree((tree) => (tree ? withSizes(tree, gutter.path, next) : tree));
    };
    const onUp = () => {
      handle.removeEventListener("pointermove", onMove);
      handle.removeEventListener("pointerup", onUp);
    };
    handle.addEventListener("pointermove", onMove);
    handle.addEventListener("pointerup", onUp);
  };

  const startResize = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.preventDefault();
    const handle = e.currentTarget;
    handle.setPointerCapture(e.pointerId);
    const from = e.clientX;
    const startWidth = width;
    const onMove = (ev: PointerEvent) => {
      const next = Math.max(DOCK_MIN, Math.min(rowWidth - CHAT_MIN, startWidth - (ev.clientX - from)));
      setDock((prev) => ({ ...prev, width: Math.round(next) }));
    };
    const onUp = () => {
      handle.removeEventListener("pointermove", onMove);
      handle.removeEventListener("pointerup", onUp);
    };
    handle.addEventListener("pointermove", onMove);
    handle.addEventListener("pointerup", onUp);
  };

  const frozen = Boolean(drag?.live) || menuFor !== null;

  if (!hasPanels) return <div ref={rootRef} className="hidden" />;

  return (
    <div
      ref={rootRef}
      className={overlay ? "absolute inset-y-0 right-0 z-30 flex bg-[var(--bg)]" : "relative flex shrink-0"}
      style={overlay ? { left: leftInset } : { width }}
    >
      {!overlay && (
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize the panels"
          title="Drag to resize"
          className="group/gutter flex w-2 shrink-0 cursor-col-resize justify-center py-3"
          onPointerDown={startResize}
        >
          <span className="w-0.5 rounded-full group-hover/gutter:bg-[color-mix(in_srgb,var(--fg)_24%,transparent)] group-active/gutter:bg-[color-mix(in_srgb,var(--fg)_58%,transparent)]" />
        </div>
      )}
      <div ref={areaRef} className={`relative my-2 mr-2 min-w-0 flex-1 ${overlay ? "ml-2" : ""}`}>
        {shown.map((id) => {
          const rect = rects[id];
          const isDragged = drag?.live && drag.id === id;
          const api: DockPanelApi = {
            id,
            headerProps: {
              onPointerDown: (e) => startDrag(id, e),
              onDoubleClick: (e) => {
                if (!(e.target as HTMLElement).closest(INTERACTIVE)) setFilled(filled === id ? null : id);
              },
            },
            controls: <DockControls id={id} title={titles[id]} actions={actions} />,
            frozen,
            hidden: !rect,
            boundsKey: rect ? `${rect.x},${rect.y},${rect.w},${rect.h},${overlay}` : "",
          };
          return (
            <section
              key={id}
              aria-label={titles[id]}
              hidden={!rect}
              className={`group/panel absolute flex flex-col overflow-hidden rounded-xl border bg-[var(--panel-bg)] ${
                isDragged
                  ? "pointer-events-none z-20 border-[var(--border-hover)] opacity-95 shadow-[0_12px_32px_rgba(0,0,0,0.18)]"
                  : "border-[var(--panel-edge)] shadow-[var(--panel-shadow)]"
              }`}
              style={
                rect
                  ? {
                      left: rect.x,
                      top: rect.y,
                      width: rect.w,
                      height: rect.h,
                      transform: isDragged ? `translate(${drag.dx}px, ${drag.dy}px)` : undefined,
                    }
                  : undefined
              }
            >
              {shown.length > 1 && !filled && (
                <div
                  title="Move"
                  className="absolute left-1/2 top-0 z-10 flex h-3 w-14 -translate-x-1/2 cursor-grab justify-center pt-1 active:cursor-grabbing"
                  onPointerDown={(e) => startDrag(id, e)}
                >
                  <span className="h-1 w-8 rounded-full bg-[var(--fg)] opacity-0 transition-opacity group-hover/panel:opacity-25 hover:!opacity-70 motion-reduce:transition-none" />
                </div>
              )}
              <DockPanelContext.Provider value={api}>{render(id)}</DockPanelContext.Provider>
            </section>
          );
        })}
        {!filled &&
          placed.gutters.map((gutter) => (
            <div
              key={`${gutter.path.join(".")}:${gutter.index}`}
              role="separator"
              aria-orientation={gutter.dir === "row" ? "vertical" : "horizontal"}
              className={`group/gutter absolute z-10 flex ${
                gutter.dir === "row" ? "cursor-col-resize justify-center py-3" : "cursor-row-resize flex-col justify-center px-3"
              }`}
              style={{ left: gutter.rect.x, top: gutter.rect.y, width: gutter.rect.w, height: gutter.rect.h }}
              onPointerDown={(e) => startGutter(gutter, e)}
            >
              <span
                className={`rounded-full group-hover/gutter:bg-[color-mix(in_srgb,var(--fg)_24%,transparent)] group-active/gutter:bg-[color-mix(in_srgb,var(--fg)_58%,transparent)] ${
                  gutter.dir === "row" ? "w-0.5" : "h-0.5"
                }`}
              />
            </div>
          ))}
        {drag?.live && drag.drop && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute z-30 rounded-full bg-[var(--accent)]"
            style={{
              left: Math.max(0, Math.min(area.w - drag.drop.line.w, drag.drop.line.x)),
              top: Math.max(0, Math.min(area.h - drag.drop.line.h, drag.drop.line.y)),
              width: drag.drop.line.w,
              height: drag.drop.line.h,
            }}
          />
        )}
      </div>
    </div>
  );
}

