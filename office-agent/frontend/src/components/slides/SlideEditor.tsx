import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { SlideChangedError, getSlideParts, saveSlideSource, type SavedSlide, type SlidePart, type SlideParts } from "../../lib/slideEditing";
import type { CommentStart } from "./SlideComments";
import { HANDLES, accentOf, labelOf, newElement, boxOf, type Insert, dragBox, elementIndexAt, elementsOf, parseSection, setBox, sourceColours, writeSection, type Box } from "../../lib/slideSource";
import { drawSection, placeNode } from "./sectionDom";
import { SlideFormatBar } from "./SlideFormatBar";
import { SlideMenu } from "./SlideMenu";
import { useFormatting } from "./useFormatting";
import { useTextEditing } from "./useTextEditing";

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
 * (Shift: 10 px), Delete to remove, Escape to let go; a double-click or Enter types into text.
 * Every change is saved at once. */
export function SlideEditor({
  threadId,
  path,
  index,
  zoom,
  refreshKey,
  firstPoint,
  onSaved,
  onProblem,
  onComment,
  insert,
  onInserted,
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
  /** Opens a new comment on an element, at its centre. */
  onComment: (at: CommentStart) => void;
  /** An element to add from the toolbar; each new object is added once. */
  insert: { what: Insert } | null;
  onInserted: () => void;
  onExit: () => void;
}) {
  const slide = useEditedSlide(threadId, path, index, refreshKey, onSaved, onProblem);
  const layerRef = useRef<HTMLDivElement>(null);
  const { hostRef, nodes } = useSectionDom(slide.doc, slide.parts, slide.drawn);
  const text = useTextEditing(slide.doc, nodes, slide.change);
  const input = useEditorInput(slide, nodes, zoom, layerRef, onExit, text.start);
  const { boxes, selected, drag, point, startDrag } = input;

  // Keys go to the editor, not to the button that started an insert.
  const focusLayer = useCallback(() => layerRef.current?.focus(), []);
  const applied = useRef<object | null>(null);
  useEffect(() => {
    if (!slide.doc || !firstPoint || applied.current === firstPoint) return;
    applied.current = firstPoint;
    startDrag(null, elementIndexAt(elementsOf(slide.doc).map(boxOf), firstPoint.x, firstPoint.y), [0, 0]);
    layerRef.current?.focus();
  }, [slide.doc, firstPoint, startDrag]);

  useInsert(insert, slide, input.select, text.start, onInserted, focusLayer);

  const shown = drag ? drag.box : selected !== null ? boxes[selected] : null;
  return (
    <div className="absolute inset-0" onKeyDown={text.onKey} onPaste={text.onPaste}>
      <div className="absolute inset-0 overflow-hidden">
        <div ref={hostRef} className="absolute left-0 top-0 origin-top-left" style={{ width: 1920, height: 1080, transform: `scale(${zoom})` }} />
      </div>
      <div
        ref={layerRef}
        tabIndex={0}
        aria-label="Slide editor"
        className={`absolute inset-0 cursor-default outline-none ${text.typing !== null ? "pointer-events-none" : ""}`}
        onPointerDown={(e) => startDrag(e, elementIndexAt(boxes, point(e).x, point(e).y), [0, 0])}
        onPointerMove={input.onMove}
        onPointerUp={input.onUp}
        onDoubleClick={(e) => {
          const at = elementIndexAt(boxes, point(e).x, point(e).y);
          if (at !== null && slide.parts[at]?.kind === "text") text.start(at, { x: e.clientX, y: e.clientY });
        }}
        onKeyDown={input.onKey}
      >
        {shown && <Selection box={shown} zoom={zoom} onHandle={(e, handle) => startDrag(e, selected, handle)} />}
      </div>
      {shown && !drag && selected !== null && (
        <EditorBar slide={slide} at={selected} box={shown} zoom={zoom} text={text} onComment={onComment} onRemoved={() => input.select(null)} />
      )}
    </div>
  );
}

/** Adds the toolbar's element to the slide, selected; a text box with its text ready to type over. */
function useInsert(
  insert: { what: Insert } | null,
  slide: ReturnType<typeof useEditedSlide>,
  select: (at: number) => void,
  startText: (at: number) => void,
  onInserted: () => void,
  focus: () => void,
) {
  const done = useRef<object | null>(null);
  useEffect(() => {
    if (!insert || !slide.doc || done.current === insert) return;
    done.current = insert;
    onInserted();
    const doc = slide.doc;
    const el = newElement(doc, insert.what, accentOf(doc));
    const at = elementsOf(doc).length;
    const isText = insert.what.kind === "text";
    slide.change(
      () => doc.documentElement.append(el),
      !isText,
      (parts) => [...parts, { kind: isText ? "text" : "drawing", box: boxOf(el), picture: null }],
    );
    select(at);
    if (isText) setTypeInto(at);
    else focus();
  }, [insert, slide, select, onInserted, focus]);

  // Typing starts once the new text box is drawn, which is after the change above renders.
  const [typeInto, setTypeInto] = useState<number | null>(null);
  useEffect(() => {
    if (typeInto === null) return;
    setTypeInto(null);
    startText(typeInto);
  }, [typeInto, startText]);
}

/** The format bar over the selection, and its More menu. */
function EditorBar({
  slide,
  at,
  box,
  zoom,
  text,
  onComment,
  onRemoved,
}: {
  slide: ReturnType<typeof useEditedSlide>;
  at: number;
  box: Box;
  zoom: number;
  text: ReturnType<typeof useTextEditing>;
  onComment: (at: CommentStart) => void;
  onRemoved: () => void;
}) {
  const [more, setMore] = useState<DOMRect | null>(null);
  const { format, actions } = useFormatting(slide.doc, at, text.typing === at, text.stop, slide.change);
  const colours = slide.doc ? sourceColours(writeSection(slide.doc)) : [];
  const [x, y, w, h] = box;
  return (
    <>
      <SlideFormatBar
        x={x * zoom}
        y={y * zoom}
        text={format}
        colours={colours}
        actions={{
          ...actions,
          comment: () => {
            const el = slide.doc && elementsOf(slide.doc)[at];
            const box: CommentStart["box"] = [x / 1920, y / 1080, w / 1920, h / 1080];
            onComment({ x: box[0] + box[2] / 2, y: box[1] + box[3] / 2, element: el ? labelOf(el) : "", box });
          },
          more: setMore,
        }}
      />
      {more && (
        <SlideMenu
          anchor={more}
          label="More"
          width={200}
          entries={arrangeEntries(slide, at, onRemoved)}
          onClose={() => setMore(null)}
        />
      )}
    </>
  );
}

/** The More menu: the element's place in the stack, a copy of it, and removing it. */
function arrangeEntries(slide: ReturnType<typeof useEditedSlide>, at: number, onRemoved: () => void) {
  const count = slide.parts.length;
  const swap = (other: number) =>
    slide.change(
      (els) => (other > at ? els[other].after(els[at]) : els[other].before(els[at])),
      false,
      (parts) => parts.map((part, i) => (i === at ? parts[other] : i === other ? parts[at] : part)),
    );
  return [
    { label: "Bring forward", disabled: at >= count - 1, onSelect: () => swap(at + 1) },
    { label: "Send backward", disabled: at <= 0, onSelect: () => swap(at - 1) },
    {
      label: "Duplicate",
      onSelect: () =>
        slide.change(
          (els) => {
            const copy = els[at].cloneNode(true) as Element;
            copy.removeAttribute("id");
            const box = boxOf(copy);
            if (box) setBox(copy, [box[0] + 24, box[1] + 24, box[2], box[3]]);
            els[at].after(copy);
          },
          false,
          (parts) => [...parts.slice(0, at + 1), parts[at], ...parts.slice(at + 1)],
        ),
    },
    {
      label: "Delete",
      hint: "Del",
      onSelect: () => {
        slide.change((els) => els[at].remove(), false, (parts) => parts.filter((_, i) => i !== at));
        onRemoved();
      },
    },
  ];
}

/** Selecting, dragging and the keys, over the slide's elements in canvas px. */
function useEditorInput(
  slide: ReturnType<typeof useEditedSlide>,
  nodes: { current: (HTMLElement | null)[] },
  zoom: number,
  layerRef: { current: HTMLDivElement | null },
  onExit: () => void,
  startText: (at: number) => void,
) {
  const [selected, setSelected] = useState<number | null>(null);
  const [drag, setDrag] = useState<Drag | null>(null);
  const boxes = slide.doc ? elementsOf(slide.doc).map(boxOf) : [];
  const place = (at: number, box: Box) => {
    const node = nodes.current[at];
    if (node) placeNode(node, box);
  };
  const point = (e: { clientX: number; clientY: number }) => {
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
    if (action === "type") return slide.parts[selected]?.kind === "text" && startText(selected);
    if (action === "delete") {
      slide.change((els) => els[selected].remove(), false, (parts) => parts.filter((_, i) => i !== selected));
      return setSelected(null);
    }
    const box = boxes[selected] && dragBox(boxes[selected], [0, 0], action[0], action[1]);
    if (!box) return;
    place(selected, box);
    slide.change((els) => setBox(els[selected], box), false);
  };
  return { boxes, selected, select: setSelected, drag, point, startDrag, onMove, onUp, onKey };
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

type EditKey = "exit" | "delete" | "type" | [number, number];

function editKey(e: KeyboardEvent): EditKey | null {
  if (e.key === "Escape") return "exit";
  if (e.key === "Enter") return "type";
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
function useSectionDom(doc: Document | null, parts: SlideParts["parts"], drawn: number) {
  const hostRef = useRef<HTMLDivElement>(null);
  const nodes = useRef<(HTMLElement | null)[]>([]);
  useLayoutEffect(() => {
    const host = hostRef.current;
    if (!host || !doc) return;
    const root = host.shadowRoot ?? host.attachShadow({ mode: "open" });
    nodes.current = drawSection(root, doc, parts);
  }, [doc, parts, drawn]);
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
  const [loaded, setLoaded] = useState<{ doc: Document; parts: SlideParts["parts"]; drawn: number } | null>(null);
  const [reads, setReads] = useState(0);
  const version = useRef("");
  const queue = useRef<Promise<void>>(Promise.resolve());
  useEffect(() => {
    let live = true;
    getSlideParts(threadId, path, index).then(
      (read) => {
        if (!live) return;
        version.current = read.version;
        setLoaded({ doc: parseSection(read.source), parts: read.parts, drawn: 0 });
      },
      (e: unknown) => live && onProblem(e instanceof Error ? e.message : String(e)),
    );
    return () => {
      live = false;
    };
  }, [threadId, path, index, refreshKey, reads, onProblem]);

  /** Applies `edit` to the section's elements, draws the slide again and saves. `redraw` reads
   * the slide from the server after, for pictures that must be drawn at a new size; `reorder`
   * keeps the parts in step with elements the edit added, took out or moved in the stack. */
  const change = (edit: (elements: Element[]) => void, redraw: boolean, reorder?: (parts: SlidePart[]) => SlidePart[]) => {
    if (!loaded) return;
    edit(elementsOf(loaded.doc));
    const source = writeSection(loaded.doc);
    setLoaded({ doc: loaded.doc, parts: reorder ? reorder(loaded.parts) : loaded.parts, drawn: loaded.drawn + 1 });
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
  return { doc: loaded?.doc ?? null, parts: loaded?.parts ?? [], drawn: loaded?.drawn ?? 0, change };
}
