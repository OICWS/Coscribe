import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import {
  applyDrop,
  arrangeAll,
  arrangementLayout,
  arrangementPanels,
  columnOf,
  COLUMN_MIN,
  dropAt,
  hintFor,
  movePanel,
  openPanel,
  withColumnTree,
  withColumnWidth,
  withoutPanel,
  type Arrangement,
  type ArrangementLayout,
  type ColumnRef,
  type Drop,
} from "../../lib/dockArrangement";
import { dragGutter, GAP, nodeAt, PANEL_IDS, withSizes, type Gutter, type PanelId, type Rect } from "../../lib/dockLayout";
import { useComposerNeededWidth } from "../../lib/composerWidth";
import { useDockLayout, type DockState } from "../../lib/useDockLayout";
import { DockControls, type DockActions } from "./DockControls";
import { DockPanelContext, type DockPanelApi } from "./dockContext";

/** The conversation keeps at least chatMin beside the panels, else they lie over it; a newly
 * opened panel gets its own column while it keeps chatMin plus CHAT_SLACK. chatMin is what the
 * composer's toolbar needs to fit on one row, never less than CHAT_FLOOR or more than CHAT_CEIL. */
const CHAT_FLOOR = 380;
const CHAT_CEIL = 900;
const CHAT_SLACK = 80;
const PANEL_MIN = 140;
const PREFERRED_WIDTH: Record<PanelId, number> = { task: 320, browser: 440, background: 440, viewer: 720, plan: 440 };
const DRAG_THRESHOLD = 5;
const NO_PANELS: Arrangement = { left: [], right: [] };

const INTERACTIVE = 'button, a, input, textarea, select, [role="tab"], [role="menuitem"], [contenteditable="true"]';

/** Brings the arrangement in line with the panels this conversation shows.
 * A closed panel leaves a hint to come back where it was; with none open
 * the arrangement is kept as it is, for the next one. */
function sync(prev: DockState, visible: readonly PanelId[], areaWidth: number, chatRoomy: number): DockState {
  if (visible.length === 0) return prev;
  let arrangement = prev.arrangement;
  const hints = { ...prev.hints };
  for (const id of arrangementPanels(arrangement)) {
    if (visible.includes(id)) continue;
    const hint = hintFor(arrangement, id);
    if (hint) hints[id] = hint;
    arrangement = withoutPanel(arrangement, id);
  }
  for (const id of visible) {
    if (arrangementPanels(arrangement).includes(id)) continue;
    const used = [...arrangement.left, ...arrangement.right].reduce((sum, c) => sum + c.width + GAP, GAP);
    const room = areaWidth - used - GAP - chatRoomy;
    arrangement = openPanel(arrangement, id, hints[id], PREFERRED_WIDTH[id], room);
  }
  return arrangement === prev.arrangement ? prev : { arrangement, hints };
}

function widthIn(arrangement: Arrangement, id: PanelId): number {
  const ref = columnOf(arrangement, id);
  return ref ? arrangement[ref.side][ref.index].width : PREFERRED_WIDTH[id];
}

interface Drag {
  id: PanelId;
  startX: number;
  startY: number;
  dx: number;
  dy: number;
  live: boolean;
  drop: Drop | null;
}

const boxStyle = (rect: Rect | undefined, extra?: CSSProperties): CSSProperties | undefined =>
  rect ? { left: rect.x, top: rect.y, width: rect.w, height: rect.h, ...extra } : undefined;

const MOVING = "transition-[left,top,width,height] duration-150 ease-out motion-reduce:transition-none";
const GUTTER_LINE =
  "rounded-full group-hover/gutter:bg-[color-mix(in_srgb,var(--fg)_24%,transparent)] group-active/gutter:bg-[color-mix(in_srgb,var(--fg)_58%,transparent)]";

/** The window below the title bar: the conversation and the side panels
 * around it, in columns on either side. Drag a header to move a panel; the
 * other panels and the conversation move to where they will be as it goes.
 * Drag a gap to resize; the expand button's menu moves, fills or arranges.
 * Every box is placed by position in one flat list, so moving a panel never
 * remounts it (the browser keeps its tabs). */
export function PanelDock({
  visible,
  titles,
  render,
  onClose,
  onPopOut,
  leftInset,
  chat,
}: {
  visible: readonly PanelId[];
  titles: Record<PanelId, string>;
  render: (id: PanelId) => ReactNode;
  onClose: (id: PanelId) => void;
  /** Opens the panel in a window of its own, from its box on screen. */
  onPopOut?: (id: PanelId, rect: Rect) => void;
  /** Room kept free at the left for the pinned sidebar. */
  leftInset: number;
  chat: ReactNode;
}) {
  const [dock, setDock] = useDockLayout();
  const [filled, setFilled] = useState<PanelId | null>(null);
  const [drag, setDrag] = useState<Drag | null>(null);
  const [menuFor, setMenuFor] = useState<PanelId | null>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const chatMin = useComposerNeededWidth(CHAT_FLOOR, CHAT_CEIL);
  const rootRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<Drag | null>(null);
  const shown = useMemo(() => PANEL_IDS.filter((id) => visible.includes(id)), [visible]);
  const visibleKey = visible.join(",");

  useLayoutEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const measure = () => setSize({ w: el.clientWidth, h: el.clientHeight });
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    measure();
    return () => observer.disconnect();
  }, []);

  const area: Rect = { x: leftInset, y: 0, w: Math.max(0, size.w - leftInset), h: size.h };

  useLayoutEffect(() => {
    if (area.w <= 0) return;
    const ids = visibleKey ? (visibleKey.split(",") as PanelId[]) : [];
    setDock((prev) => sync(prev, ids, area.w, chatMin + CHAT_SLACK));
    // Only a change in which panels show re-places them, not every resize.
  }, [visibleKey, area.w > 0, setDock]); // oxlint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (filled && !visible.includes(filled)) setFilled(null);
  }, [filled, visible]);

  const arrangement = shown.length > 0 ? dock.arrangement : NO_PANELS;
  const placed: ArrangementLayout = arrangementLayout(arrangement, area, chatMin);
  const preview =
    drag?.live && drag.drop
      ? arrangementLayout(applyDrop(arrangement, drag.id, drag.drop, widthIn(arrangement, drag.id)), area, chatMin)
      : null;
  const shownLayout = preview ?? placed;

  const setArrangement = useCallback(
    (update: (a: Arrangement) => Arrangement) => setDock((prev) => ({ ...prev, arrangement: update(prev.arrangement) })),
    [setDock],
  );
  const setMenuOpen = useCallback(
    (id: PanelId, open: boolean) => setMenuFor((current) => (open ? id : current === id ? null : current)),
    [],
  );

  const actions: DockActions = {
    filled,
    panelCount: shown.length,
    edgeOf: (id) => (filled ? null : (columnOf(arrangement, id)?.side ?? null)),
    move: (id, edge) => {
      setFilled(null);
      setArrangement((a) => movePanel(a, id, edge, widthIn(a, id)));
    },
    fill: setFilled,
    arrange: (dir) => {
      setFilled(null);
      setArrangement((a) => arrangeAll(a, dir));
    },
    close: onClose,
    setMenuOpen,
    popOut: onPopOut && ((id) => popOutFrom(rootRef.current, id, onPopOut, () => setFilled(null))),
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
    if (e.button !== 0 || filled) return;
    if ((e.target as HTMLElement).closest(INTERACTIVE)) return;
    dragRef.current = { id, startX: e.clientX, startY: e.clientY, dx: 0, dy: 0, live: false, drop: null };
    const onMove = (ev: PointerEvent) => {
      const current = dragRef.current;
      if (!current) return;
      const dx = ev.clientX - current.startX;
      const dy = ev.clientY - current.startY;
      if (!current.live && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
      if (!current.live) document.body.style.userSelect = "none";
      const box = rootRef.current?.getBoundingClientRect();
      const drop = box ? dropAt(placed, arrangement, area, current.id, ev.clientX - box.left, ev.clientY - box.top) : null;
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
        const drop = done.drop;
        setArrangement((a) => applyDrop(a, done.id, drop, widthIn(a, done.id)));
      }
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
  };

  const track = (e: ReactPointerEvent<HTMLDivElement>, onMove: (ev: PointerEvent) => void) => {
    e.preventDefault();
    const handle = e.currentTarget;
    handle.setPointerCapture(e.pointerId);
    const onUp = () => {
      handle.removeEventListener("pointermove", onMove);
      handle.removeEventListener("pointerup", onUp);
    };
    handle.addEventListener("pointermove", onMove);
    handle.addEventListener("pointerup", onUp);
  };

  const startGutter = (gutter: Gutter & { column: ColumnRef }, e: ReactPointerEvent<HTMLDivElement>) => {
    const column = arrangement[gutter.column.side][gutter.column.index];
    const split = column ? nodeAt(column.tree, gutter.path) : null;
    if (e.button !== 0 || !split || split.kind !== "split") return;
    const sizes = split.sizes;
    const from = gutter.dir === "row" ? e.clientX : e.clientY;
    const min = gutter.dir === "row" ? COLUMN_MIN / 2 : PANEL_MIN;
    track(e, (ev) => {
      const delta = (gutter.dir === "row" ? ev.clientX : ev.clientY) - from;
      const next = dragGutter(sizes, gutter.index, delta, gutter.length, min);
      setArrangement((a) => {
        const current = a[gutter.column.side][gutter.column.index];
        return current ? withColumnTree(a, gutter.column, withSizes(current.tree, gutter.path, next)) : a;
      });
    });
  };

  const startColumnResize = (ref: ColumnRef, e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    const start = arrangement[ref.side][ref.index]?.width ?? COLUMN_MIN;
    const from = e.clientX;
    const others = [...arrangement.left, ...arrangement.right].reduce((sum, c) => sum + c.width + GAP, GAP) - start;
    const max = Math.max(COLUMN_MIN, area.w - others - GAP - chatMin);
    track(e, (ev) => {
      const delta = (ev.clientX - from) * (ref.side === "left" ? 1 : -1);
      setArrangement((a) => withColumnWidth(a, ref, Math.max(COLUMN_MIN, Math.min(max, start + delta))));
    });
  };

  const frozen = Boolean(drag?.live) || menuFor !== null;
  const dragged = drag?.live ? drag.id : null;
  const fillRect: Rect = { x: area.x + GAP, y: GAP, w: Math.max(0, area.w - 2 * GAP), h: Math.max(0, area.h - 2 * GAP) };
  const resizable = !filled && !dragged;

  return (
    <div ref={rootRef} className="relative min-h-0 min-w-0 flex-1 overflow-hidden">
      <div
        hidden={filled !== null}
        className={`absolute flex flex-col ${dragged ? MOVING : ""}`}
        style={boxStyle(shownLayout.chat)}
      >
        {chat}
      </div>
      {shown.map((id) => {
        let rect: Rect | undefined;
        if (filled) rect = filled === id ? fillRect : undefined;
        else rect = dragged === id ? placed.panels[id] : shownLayout.panels[id];
        const isDragged = dragged === id;
        const api: DockPanelApi = {
          id,
          headerProps: {
            onPointerDown: (e) => startDrag(id, e),
            onDoubleClick: (e) => {
              if (!(e.target as HTMLElement).closest(INTERACTIVE)) setFilled(filled === id ? null : id);
            },
            "data-dock-header": true,
          },
          controls: <DockControls id={id} title={titles[id]} actions={actions} />,
          frozen,
          hidden: !rect,
          boundsKey: rect ? `${rect.x},${rect.y},${rect.w},${rect.h}` : "",
        };
        const look = isDragged
          ? "pointer-events-none z-30 border-[var(--border-hover)] opacity-95 shadow-[0_12px_32px_rgba(0,0,0,0.18)]"
          : `z-10 border-[var(--panel-edge)] shadow-[var(--panel-shadow)] ${dragged ? MOVING : ""}`;
        return (
          <section
            key={id}
            data-panel={id}
            aria-label={titles[id]}
            hidden={!rect}
            className={`group/panel absolute flex flex-col overflow-hidden rounded-xl border bg-[var(--panel-bg)] ${look}`}
            style={boxStyle(rect, isDragged && drag ? { transform: `translate(${drag.dx}px, ${drag.dy}px)` } : undefined)}
          >
            {!filled && <MoveGrip onPointerDown={(e) => startDrag(id, e)} />}
            <DockPanelContext.Provider value={api}>{render(id)}</DockPanelContext.Provider>
          </section>
        );
      })}
      {dragged && preview?.panels[dragged] && (
        <div
          aria-hidden="true"
          className={`pointer-events-none absolute z-20 rounded-xl bg-[var(--accent-soft)] ${MOVING}`}
          style={boxStyle(preview.panels[dragged])}
        />
      )}
      {resizable &&
        placed.gutters.map((gutter) => (
          <div
            key={`${gutter.column.side}${gutter.column.index}:${gutter.path.join(".")}:${gutter.index}`}
            role="separator"
            aria-orientation={gutter.dir === "row" ? "vertical" : "horizontal"}
            className={`group/gutter absolute z-10 flex ${
              gutter.dir === "row" ? "cursor-col-resize justify-center py-3" : "cursor-row-resize flex-col justify-center px-3"
            }`}
            style={boxStyle(gutter.rect)}
            onPointerDown={(e) => startGutter(gutter, e)}
          >
            <span className={`${GUTTER_LINE} ${gutter.dir === "row" ? "w-0.5" : "h-0.5"}`} />
          </div>
        ))}
      {resizable &&
        placed.columnGutters.map(({ column, rect }) => (
          <div
            key={`column:${column.side}${column.index}`}
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize the panels"
            className="group/gutter absolute z-10 flex cursor-col-resize justify-center py-3"
            style={boxStyle(rect)}
            onPointerDown={(e) => startColumnResize(column, e)}
          >
            <span className={`${GUTTER_LINE} w-0.5`} />
          </div>
        ))}
    </div>
  );
}

/** The bar at a panel's top edge to drag it by. */
function MoveGrip({ onPointerDown }: { onPointerDown: (e: React.PointerEvent<HTMLDivElement>) => void }) {
  return (
    <div
      title="Move"
      className="absolute left-1/2 top-0 z-10 flex h-3 w-14 -translate-x-1/2 cursor-grab justify-center pt-1 active:cursor-grabbing"
      onPointerDown={onPointerDown}
    >
      <span className="h-1 w-8 rounded-full bg-[var(--fg)] opacity-0 transition-opacity group-hover/panel:opacity-25 hover:!opacity-70 motion-reduce:transition-none" />
    </div>
  );
}

function popOutFrom(root: HTMLElement | null, id: PanelId, onPopOut: (id: PanelId, rect: Rect) => void, unfill: () => void) {
  const box = root?.querySelector(`section[data-panel="${id}"]`)?.getBoundingClientRect();
  unfill();
  if (box) onPopOut(id, { x: box.left, y: box.top, w: box.width, h: box.height });
}
