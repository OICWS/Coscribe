import { useCallback, useRef, type Dispatch, type PointerEvent as ReactPointerEvent, type SetStateAction } from "react";
import { placeOnCanvas, type Canvas, type CanvasNote, type View } from "../../lib/designCanvas";

export type Tool = "select" | "hand" | "note";

/** A press that moves something: the canvas itself, a board or a note, from where it started. */
interface Drag {
  kind: "pan" | "board" | "note";
  id?: string;
  startX: number;
  startY: number;
  originX: number;
  originY: number;
  moved: boolean;
}

interface Editing {
  threadId: string;
  path: string;
  canvas: Canvas | null;
  setCanvas: (canvas: Canvas) => void;
  view: View;
  setView: Dispatch<SetStateAction<View>>;
  toCanvas: (clientX: number, clientY: number) => { x: number; y: number };
  onProblem: (problem: string) => void;
}

/** What the pointer does on the canvas: pan it, move a board or a note, leave a note; every move
 * that ends is saved to the canvas file. */
export function useCanvasEditing({ threadId, path, canvas, setCanvas, view, setView, toCanvas, onProblem }: Editing) {
  const drag = useRef<Drag | null>(null);

  const save = useCallback(
    (boards: Parameters<typeof placeOnCanvas>[2], notes?: CanvasNote[]) => {
      placeOnCanvas(threadId, path, boards, notes)
        .then(setCanvas)
        .catch((e: unknown) => onProblem(e instanceof Error ? e.message : String(e)));
    },
    [threadId, path, setCanvas, onProblem],
  );

  const start = (e: ReactPointerEvent, kind: Drag["kind"], id?: string) => {
    if (!canvas) return;
    e.stopPropagation();
    (e.target as Element).setPointerCapture(e.pointerId);
    const item = kind === "board" ? canvas.boards.find((b) => b.id === id) : kind === "note" ? canvas.notes.find((n) => n.id === id) : null;
    drag.current = { kind, id, startX: e.clientX, startY: e.clientY, originX: item ? item.x : view.x, originY: item ? item.y : view.y, moved: false };
  };

  /** A new note where the canvas was pressed, its text box open; returns its id. */
  const addNote = (e: ReactPointerEvent): string | null => {
    if (!canvas) return null;
    // Else the press moves the focus away from the new note's text box as soon as it opens.
    e.preventDefault();
    const at = toCanvas(e.clientX, e.clientY);
    const note: CanvasNote = { id: `note-${Date.now().toString(36)}`, text: "Note", x: at.x, y: at.y, width: 220, color: "yellow" };
    const notes = [...canvas.notes, note];
    setCanvas({ ...canvas, notes });
    save({}, notes);
    return note.id;
  };

  const move = (e: ReactPointerEvent) => {
    const d = drag.current;
    if (!d || !canvas) return;
    const dx = e.clientX - d.startX;
    const dy = e.clientY - d.startY;
    if (Math.abs(dx) + Math.abs(dy) > 2) d.moved = true;
    const to = { x: d.originX + dx / view.zoom, y: d.originY + dy / view.zoom };
    if (d.kind === "pan") setView((v) => ({ ...v, x: d.originX - dx / v.zoom, y: d.originY - dy / v.zoom }));
    else if (d.kind === "board") setCanvas({ ...canvas, boards: canvas.boards.map((b) => (b.id === d.id ? { ...b, ...to } : b)) });
    else setCanvas({ ...canvas, notes: canvas.notes.map((n) => (n.id === d.id ? { ...n, ...to } : n)) });
  };

  const end = () => {
    const d = drag.current;
    drag.current = null;
    if (!d || !d.moved || !canvas) return;
    if (d.kind === "board") {
      const board = canvas.boards.find((b) => b.id === d.id);
      if (board) save({ [board.id]: { x: Math.round(board.x), y: Math.round(board.y) } });
    } else if (d.kind === "note") {
      save({}, canvas.notes);
    }
  };

  /** A note's new text; an empty one deletes the note. */
  const editNote = (id: string, text: string) => {
    if (!canvas) return;
    const notes = text.trim() ? canvas.notes.map((n) => (n.id === id ? { ...n, text } : n)) : canvas.notes.filter((n) => n.id !== id);
    setCanvas({ ...canvas, notes });
    save({}, notes);
  };

  return { start, addNote, move, end, editNote };
}
