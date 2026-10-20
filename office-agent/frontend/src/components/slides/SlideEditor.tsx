import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { siblingOf, type Drop } from "../../lib/slideStacks";
import { SlideChangedError, getSlideParts, saveSlideSource, uploadSlidePicture, type SavedSlide, type SlidePart, type SlideParts } from "../../lib/slideEditing";
import type { CommentStart } from "./SlideComments";
import { HANDLES, STACK, accentOf, boxOf, boxOnSlide, dragBox, elementIndexAt, elementsOf, inStack, labelOf, newElement, parseSection, setBox, type Insert, sourceColours, writeSection, type Box } from "../../lib/slideSource";
import { drawSection, placeNode } from "./sectionDom";
import { SlideFormatBar } from "./SlideFormatBar";
import type { MenuEntry } from "./SlideMenu";
import type { EditorSelection } from "./SlideTextProperties";
import { useFormatting } from "./useFormatting";
import { useStackDrop } from "./useStackDrop";
import { useTableEditing } from "./useTableEditing";
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
  onSelection,
  onMore,
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
  /** The selected text element, for the properties panel; null when nothing or no text is. */
  onSelection: (selection: EditorSelection | null) => void;
  /** The format bar's ⋮: shows the properties panel. */
  onMore: () => void;
  /** An element to add from the toolbar; each new object is added once. */
  insert: { what: Insert } | null;
  onInserted: () => void;
  onExit: () => void;
}) {
  const slide = useEditedSlide(threadId, path, index, refreshKey, onSaved, onProblem);
  const layerRef = useRef<HTMLDivElement>(null);
  const tableAt = useState<number | null>(null);
  const { hostRef, nodes } = useSectionDom(slide.doc, slide.parts, slide.drawn, tableAt[0]);
  const text = useTextEditing(slide.doc, nodes, slide.change);
  const table = useTableEditing(slide.doc, nodes, slide.change, tableAt);
  const startTyping = (at: number, point?: { x: number; y: number }) =>
    isTable(slide.doc, at) ? table.start(at, point) : text.start(at, point);
  const input = useEditorInput(slide, nodes, zoom, layerRef, onExit, startTyping);
  const { boxes, selected, drag, drop, point, startDrag } = input;

  usePublishedSelection(slide, selected, () => (text.stop(), table.stop()), (file) => uploadSlidePicture(threadId, path, file), () => input.select(null), onSelection);

  // Keys go to the editor, not to the button that started an insert.
  const focusLayer = useCallback(() => layerRef.current?.focus(), []);
  const applied = useRef<object | null>(null);
  useEffect(() => {
    if (!slide.doc || !firstPoint || applied.current === firstPoint) return;
    applied.current = firstPoint;
    startDrag(null, elementIndexAt(nodeBoxes(slide.doc, slide.parts), firstPoint.x, firstPoint.y), [0, 0]);
    layerRef.current?.focus();
  }, [slide.doc, firstPoint, startDrag]);

  useInsert(insert, slide, input.select, text.start, onInserted, focusLayer);

  const shown = drag ? drag.box : selected !== null ? boxes[selected] : null;
  const placedByLayout = selected !== null && !!slide.doc && inStack(elementsOf(slide.doc)[selected] ?? slide.doc.documentElement);
  return (
    <div
      className="absolute inset-0"
      onKeyDown={(e) => (text.onKey(e), table.onKey(e))}
      onPaste={(e) => (text.onPaste(e), table.onPaste(e))}
    >
      <div className="absolute inset-0 overflow-hidden">
        <div ref={hostRef} className="absolute left-0 top-0 origin-top-left" style={{ width: 1920, height: 1080, transform: `scale(${zoom})` }} />
      </div>
      <div
        ref={layerRef}
        tabIndex={0}
        aria-label="Slide editor"
        className={`absolute inset-0 cursor-default outline-none ${text.typing !== null || table.editing !== null ? "pointer-events-none" : ""}`}
        onPointerDown={(e) => startDrag(e, elementIndexAt(boxes, point(e).x, point(e).y), [0, 0])}
        onPointerMove={input.onMove}
        onPointerUp={input.onUp}
        onDoubleClick={(e) => {
          const at = elementIndexAt(boxes, point(e).x, point(e).y);
          if (at !== null && (slide.parts[at]?.kind === "text" || isTable(slide.doc, at))) startTyping(at, { x: e.clientX, y: e.clientY });
        }}
        onKeyDown={input.onKey}
      >
        {drop && <DropMark drop={drop} zoom={zoom} />}
        {shown && <Selection box={shown} zoom={zoom} handles={!placedByLayout} onHandle={(e, handle) => startDrag(e, selected, handle)} />}
      </div>
      {shown && !drag && selected !== null && (
        <EditorBar slide={slide} at={selected} box={shown} zoom={zoom} text={text} onComment={onComment} onMore={onMore} />
      )}
    </div>
  );
}

const KINDS: Record<string, EditorSelection["kind"]> = { h1: "text", h2: "text", h3: "text", p: "text", ul: "text", ol: "text", table: "table", img: "image", "x-shape": "shape", "x-chart": "chart", [STACK]: "container" };

const isTable = (doc: Document | null, at: number) => !!doc && elementsOf(doc)[at]?.localName === "table";

/** Tells the properties panel which text element is selected, after every change to it; a change
 * made there ends any typing first, so what was typed is written back. */
function usePublishedSelection(
  slide: ReturnType<typeof useEditedSlide>,
  selected: number | null,
  stopTyping: () => void,
  upload: NonNullable<EditorSelection["upload"]>,
  onRemoved: () => void,
  publish: (selection: EditorSelection | null) => void,
) {
  const { doc, drawn } = slide;
  // The latest functions, so a render alone does not publish a new selection.
  const latest = useRef({ change: slide.change, stop: stopTyping, upload, publish });
  latest.current = { change: slide.change, stop: stopTyping, upload, publish };
  const removed = useRef(onRemoved);
  removed.current = onRemoved;
  useEffect(() => {
    const element = doc && selected !== null ? elementsOf(doc)[selected] : null;
    const kind = element && KINDS[element.localName];
    latest.current.publish(
      element && kind && selected !== null
        ? {
            kind,
            element,
            edit: (edit, redraw = false) => {
              latest.current.stop();
              latest.current.change((els) => edit(els[selected]), redraw || kind === "table" || kind === "chart");
            },
            upload: latest.current.upload,
            arrange: arrangeEntries(slide, selected, () => removed.current()),
          }
        : null,
    );
    // `drawn` counts the changes, which edit the element in place.
  }, [doc, drawn, selected]);
  useEffect(() => () => latest.current.publish(null), []);
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
  onMore,
}: {
  slide: ReturnType<typeof useEditedSlide>;
  at: number;
  box: Box;
  zoom: number;
  text: ReturnType<typeof useTextEditing>;
  onComment: (at: CommentStart) => void;
  onMore: () => void;
}) {
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
          more: onMore,
        }}
      />
    </>
  );
}

/** The properties panel's Arrange section: the element's place in the stack, a copy of it, and removing it. */
function arrangeEntries(slide: ReturnType<typeof useEditedSlide>, at: number, onRemoved: () => void): MenuEntry[] {
  const el = slide.doc ? elementsOf(slide.doc)[at] : null;
  // The next or previous element among those of the same parent: on the slide, its stacking
  // order; in a container, its place in the layout.
  const swap = (step: 1 | -1) =>
    slide.change(
      (els) => {
        const other = siblingOf(els[at], step);
        if (other) step > 0 ? other.after(els[at]) : other.before(els[at]);
      },
      false,
      // Parts follow by position when nothing is nested (the editor reads the slide again otherwise).
      (parts) => parts.map((part, i) => (i === at ? parts[at + step] : i === at + step ? parts[at] : part)),
    );
  return [
    { label: "Bring forward", disabled: !el || !siblingOf(el, 1), onSelect: () => swap(1) },
    { label: "Send backward", disabled: !el || !siblingOf(el, -1), onSelect: () => swap(-1) },
    {
      label: "Duplicate",
      onSelect: () =>
        slide.change(
          (els) => {
            const copy = els[at].cloneNode(true) as Element;
            copy.removeAttribute("id");
            const box = boxOf(copy);
            if (box && !inStack(els[at])) setBox(copy, [box[0] + 24, box[1] + 24, box[2], box[3]]);
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

const hasStack = (doc: Document) => elementsOf(doc).some((el) => el.localName === STACK);

/** Every element's box on the slide, in the section's order. */
function nodeBoxes(doc: Document, parts: SlidePart[]): (Box | null)[] {
  return elementsOf(doc).map((el, i) => boxOnSlide(el, parts[i]?.box));
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
  const boxes = slide.doc ? nodeBoxes(slide.doc, slide.parts) : [];
  const stackDrop = useStackDrop(slide.doc, boxes, slide.change, setSelected);
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
      const el = at === null ? null : elementsOf(slide.doc!)[at];
      const box = el ? boxOnSlide(el, slide.parts[at!]?.box) : null;
      // What a container places can be moved (into, within or out of containers) but not resized by hand.
      if (!e || !el || !box || (inStack(el) && (handle[0] !== 0 || handle[1] !== 0))) return;
      e.currentTarget.setPointerCapture(e.pointerId);
      layerRef.current?.focus({ preventScroll: true });
      const rect = layerRef.current!.getBoundingClientRect();
      setDrag({ index: at as number, handle, start: box, box, x: (e.clientX - rect.left) / zoom, y: (e.clientY - rect.top) / zoom });
    },
    [slide.doc, slide.parts, zoom, layerRef],
  );
  const onMove = (e: PointerEvent) => {
    if (!drag) return;
    const now = point(e);
    const box = dragBox(drag.start, drag.handle, now.x - drag.x, now.y - drag.y, e.shiftKey);
    place(drag.index, box);
    setDrag({ ...drag, box });
    if (drag.handle[0] === 0 && drag.handle[1] === 0) stackDrop.track(drag.index, now.x, now.y);
  };
  const onUp = () => {
    if (!drag) return;
    setDrag(null);
    // A change redraws the slide, which drops focus; the keys (Ctrl+Z, arrows, Delete) need it back.
    requestAnimationFrame(() => layerRef.current?.focus({ preventScroll: true }));
    const moved = drag.box.some((v, i) => Math.abs(v - drag.start[i]) >= DRAG_FROM);
    if (moved && drag.handle[0] === 0 && drag.handle[1] === 0 && stackDrop.finish(drag.index, drag.box)) return;
    stackDrop.clear();
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
    if (action === "type") return (slide.parts[selected]?.kind === "text" || isTable(slide.doc, selected)) && startText(selected);
    if (action === "delete") {
      slide.change((els) => els[selected].remove(), false, (parts) => parts.filter((_, i) => i !== selected));
      return setSelected(null);
    }
    const box = boxes[selected] && dragBox(boxes[selected], [0, 0], action[0], action[1]);
    if (!box || inStack(elementsOf(slide.doc!)[selected])) return;
    place(selected, box);
    slide.change((els) => setBox(els[selected], box), false);
  };
  return { boxes, selected, select: setSelected, drag, drop: stackDrop.drop, point, startDrag, onMove, onUp, onKey };
}

/** The container an element would drop into, and the line where it would go. */
function DropMark({ drop, zoom }: { drop: Drop; zoom: number }) {
  const place = ([x, y, w, h]: Box) => ({ left: x * zoom, top: y * zoom, width: w * zoom, height: h * zoom });
  return (
    <>
      <div className="pointer-events-none absolute rounded border-2 border-dashed border-[var(--accent)]" style={place(drop.box)} />
      <div className="pointer-events-none absolute rounded bg-[var(--accent)]" style={place(drop.line)} />
    </>
  );
}

function Selection({ box, zoom, handles, onHandle }: { box: Box; zoom: number; handles: boolean; onHandle: (e: PointerEvent, handle: [number, number]) => void }) {
  const [x, y, w, h] = box.map((v) => v * zoom);
  return (
    <div className="pointer-events-none absolute border-2 border-[var(--accent)]" style={{ left: x - 1, top: y - 1, width: w + 2, height: h + 2 }}>
      {(handles ? HANDLES : []).map(([hx, hy]) => (
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
function useSectionDom(doc: Document | null, parts: SlideParts["parts"], drawn: number, editing: number | null) {
  const hostRef = useRef<HTMLDivElement>(null);
  const nodes = useRef<(HTMLElement | null)[]>([]);
  useLayoutEffect(() => {
    const host = hostRef.current;
    if (!host || !doc) return;
    const root = host.shadowRoot ?? host.attachShadow({ mode: "open" });
    nodes.current = drawSection(root, doc, parts, editing);
  }, [doc, parts, drawn, editing]);
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
    const hadStack = hasStack(loaded.doc);
    edit(elementsOf(loaded.doc));
    const source = writeSection(loaded.doc);
    // Where a container puts what it holds is the server's layout: the slide is read again.
    const laidOut = hadStack || hasStack(loaded.doc);
    redraw = redraw || laidOut;
    setLoaded({ doc: loaded.doc, parts: reorder && !laidOut ? reorder(loaded.parts) : loaded.parts, drawn: loaded.drawn + 1 });
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
