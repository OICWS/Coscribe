import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { SlideChangedError, getSlideParts, saveSlideSource, type SavedSlide, type SlideParts } from "../../lib/slideEditing";
import { HANDLES, boxOf, dragBox, elementIndexAt, elementsOf, parseSection, setBox, writeSection, type Box } from "../../lib/slideSource";
import { drawSection, placeNode } from "./sectionDom";

/** A move shorter than this (canvas px) is a click, not a drag. */
const DRAG_FROM = 2;

interface Drag {
  index: number;
  handle: [number, number];
  start: Box;
  x: number;
  y: number;
  box: Box;
}

/** The slide being edited, drawn as the page's own elements over its picture: click to select,
 * drag to move, a handle to resize (Shift keeps proportions from a corner), arrows to nudge
 * (Shift: 10 px), Delete to remove, Escape to let go. Every change is saved at once. */
export function SlideEditor({
  threadId,
  path,
  index,
  zoom,
  refreshKey,
  firstPoint,
  onSaved,
  onProblem,
  onExit,
}: {
  threadId: string;
  path: string;
  index: number;
  zoom: number;
  /** Changes when coscribe rebuilt the deck: the slide is read again. */
  refreshKey: string;
  /** Where the click that started editing was (canvas px), to select what is there. */
  firstPoint: { x: number; y: number } | null;
  onSaved: (saved: SavedSlide) => void;
  onProblem: (message: string | null) => void;
  onExit: () => void;
}) {
  const slide = useEditedSlide(threadId, path, index, refreshKey, onSaved, onProblem);
  const layerRef = useRef<HTMLDivElement>(null);
  const { hostRef, nodes } = useSectionDom(slide.doc, slide.parts);
  const { boxes, selected, drag, point, startDrag, onMove, onUp, onKey } = useEditorInput(slide, nodes, zoom, layerRef, onExit);

  const applied = useRef<object | null>(null);
  useEffect(() => {
    if (!slide.doc || !firstPoint || applied.current === firstPoint) return;
    applied.current = firstPoint;
    startDrag(null, elementIndexAt(elementsOf(slide.doc).map(boxOf), firstPoint.x, firstPoint.y), [0, 0]);
    layerRef.current?.focus();
  }, [slide.doc, firstPoint, startDrag]);

  const shown = drag ? drag.box : selected !== null ? boxes[selected] : null;
  return (
    <div className="absolute inset-0 overflow-hidden">
      <div
        ref={hostRef}
        className="absolute left-0 top-0 origin-top-left"
        style={{ width: 1920, height: 1080, transform: `scale(${zoom})` }}
      />
      <div
        ref={layerRef}
        tabIndex={0}
        aria-label="Slide editor"
        className="absolute inset-0 cursor-default outline-none"
        onPointerDown={(e) => startDrag(e, elementIndexAt(boxes, point(e).x, point(e).y), [0, 0])}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onKeyDown={onKey}
      >
        {shown && <Selection box={shown} zoom={zoom} onHandle={(e, handle) => startDrag(e, selected, handle)} />}
      </div>
    </div>
  );
}

/** Selecting, dragging and the keys, over the slide's elements in canvas px. */
function useEditorInput(
  slide: ReturnType<typeof useEditedSlide>,
  nodes: { current: (HTMLElement | null)[] },
  zoom: number,
  layerRef: { current: HTMLDivElement | null },
  onExit: () => void,
) {
  const [selected, setSelected] = useState<number | null>(null);
  const [drag, setDrag] = useState<Drag | null>(null);
  const boxes = slide.doc ? elementsOf(slide.doc).map(boxOf) : [];
  const place = (at: number, box: Box) => {
    const node = nodes.current[at];
    if (node) placeNode(node, box);
  };
  const point = (e: PointerEvent) => {
    const rect = layerRef.current!.getBoundingClientRect();
    return { x: (e.clientX - rect.left) / zoom, y: (e.clientY - rect.top) / zoom };
  };
  /** Selects `at`; with a pointer down, also starts dragging it by `handle`. */
  const startDrag = useCallback(
    (e: PointerEvent | null, at: number | null, handle: [number, number]) => {
      setSelected(at);
      const box = at === null ? null : boxOf(elementsOf(slide.doc!)[at]);
      if (!e || at === null || !box) return;
      e.currentTarget.setPointerCapture(e.pointerId);
      const rect = layerRef.current!.getBoundingClientRect();
      setDrag({ index: at, handle, start: box, box, x: (e.clientX - rect.left) / zoom, y: (e.clientY - rect.top) / zoom });
    },
    [slide.doc, zoom, layerRef],
  );
  const onMove = (e: PointerEvent) => {
    if (!drag) return;
    const now = point(e);
    const box = dragBox(drag.start, drag.handle, now.x - drag.x, now.y - drag.y, e.shiftKey);
    place(drag.index, box);
    setDrag({ ...drag, box });
  };
  const onUp = () => {
    if (!drag) return;
    setDrag(null);
    const moved = drag.box.some((v, i) => Math.abs(v - drag.start[i]) >= DRAG_FROM);
    if (moved) slide.change((els) => setBox(els[drag.index], drag.box), drag.handle[0] !== 0 || drag.handle[1] !== 0);
    else place(drag.index, drag.start);
  };
  const onKey = (e: KeyboardEvent) => {
    const action = editKey(e);
    if (action === null) return;
    e.preventDefault();
    e.stopPropagation();
    if (action === "exit") return selected === null ? onExit() : setSelected(null);
    if (selected === null) return;
    if (action === "delete") {
      slide.change((els) => els[selected].remove(), false, selected);
      return setSelected(null);
    }
    const box = boxes[selected] && dragBox(boxes[selected], [0, 0], action[0], action[1]);
    if (!box) return;
    place(selected, box);
    slide.change((els) => setBox(els[selected], box), false);
  };
  return { boxes, selected, drag, point, startDrag, onMove, onUp, onKey };
}

function Selection({ box, zoom, onHandle }: { box: Box; zoom: number; onHandle: (e: PointerEvent, handle: [number, number]) => void }) {
  const [x, y, w, h] = box.map((v) => v * zoom);
  return (
    <div className="pointer-events-none absolute border-2 border-[var(--accent)]" style={{ left: x - 1, top: y - 1, width: w + 2, height: h + 2 }}>
      {HANDLES.map(([hx, hy]) => (
        <span
          key={`${hx}${hy}`}
          aria-hidden
          className="pointer-events-auto absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 border-2 border-[var(--accent)] bg-white"
          style={{
            left: `${(hx + 1) * 50}%`,
            top: `${(hy + 1) * 50}%`,
            cursor: hx === 0 ? "ns-resize" : hy === 0 ? "ew-resize" : hx === hy ? "nwse-resize" : "nesw-resize",
          }}
          onPointerDown={(e) => {
            e.stopPropagation();
            onHandle(e, [hx, hy]);
          }}
        />
      ))}
    </div>
  );
}

type EditKey = "exit" | "delete" | [number, number];

function editKey(e: KeyboardEvent): EditKey | null {
  if (e.key === "Escape") return "exit";
  if (e.key === "Delete" || e.key === "Backspace") return "delete";
  const step = e.shiftKey ? 10 : 1;
  const arrows: Record<string, [number, number]> = {
    ArrowLeft: [-step, 0],
    ArrowRight: [step, 0],
    ArrowUp: [0, -step],
    ArrowDown: [0, step],
  };
  return arrows[e.key] ?? null;
}

/** The section drawn into a shadow root on the host; its nodes, for moving them while dragged. */
function useSectionDom(doc: Document | null, parts: SlideParts["parts"]) {
  const hostRef = useRef<HTMLDivElement>(null);
  const nodes = useRef<(HTMLElement | null)[]>([]);
  useLayoutEffect(() => {
    const host = hostRef.current;
    if (!host || !doc) return;
    const root = host.shadowRoot ?? host.attachShadow({ mode: "open" });
    nodes.current = drawSection(root, doc, parts);
  }, [doc, parts]);
  return { hostRef, nodes };
}

/** The slide's source as the editor holds it, read from the server and saved back one change
 * at a time, each save naming the version the last one left. */
function useEditedSlide(
  threadId: string,
  path: string,
  index: number,
  refreshKey: string,
  onSaved: (saved: SavedSlide) => void,
  onProblem: (message: string | null) => void,
) {
  const [loaded, setLoaded] = useState<{ doc: Document; parts: SlideParts["parts"] } | null>(null);
  const [reads, setReads] = useState(0);
  const version = useRef("");
  const queue = useRef<Promise<void>>(Promise.resolve());
  useEffect(() => {
    let live = true;
    getSlideParts(threadId, path, index).then(
      (read) => {
        if (!live) return;
        version.current = read.version;
        setLoaded({ doc: parseSection(read.source), parts: read.parts });
      },
      (e: unknown) => live && onProblem(e instanceof Error ? e.message : String(e)),
    );
    return () => {
      live = false;
    };
  }, [threadId, path, index, refreshKey, reads, onProblem]);

  /** Applies `edit` to the section's elements and saves. `redraw` reads the slide again after,
   * for pictures that must be drawn at a new size; `removed` is an element the edit took out. */
  const change = (edit: (elements: Element[]) => void, redraw: boolean, removed?: number) => {
    if (!loaded) return;
    edit(elementsOf(loaded.doc));
    const source = writeSection(loaded.doc);
    const parts = removed === undefined ? loaded.parts : loaded.parts.filter((_, i) => i !== removed);
    setLoaded({ doc: loaded.doc, parts });
    queue.current = queue.current.then(() =>
      saveSlideSource(threadId, path, index, source, version.current).then(
        (saved) => {
          version.current = saved.version;
          onProblem(saved.problems[0] ?? null);
          onSaved(saved);
          if (redraw) setReads((n) => n + 1);
        },
        (e: unknown) => {
          onProblem(e instanceof Error ? e.message : String(e));
          if (e instanceof SlideChangedError && e.what === "slide") setReads((n) => n + 1);
        },
      ),
    );
  };
  return { doc: loaded?.doc ?? null, parts: loaded?.parts ?? [], change };
}
