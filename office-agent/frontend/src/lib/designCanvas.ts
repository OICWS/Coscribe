/** A Design canvas as the server reads it (`conversation/design_canvas.py`): artboards placed on a
 * canvas, each a page of its own, and the person's notes. */

export interface CanvasBoard {
  id: string;
  title: string;
  file: string;
  /** The workspace path its page is served by. */
  path: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface CanvasNote {
  id: string;
  text: string;
  x: number;
  y: number;
  width: number;
  color: "yellow" | "pink" | "blue" | "green";
}

export interface Canvas {
  boards: CanvasBoard[];
  notes: CanvasNote[];
}

/** Where the canvas is looked at from: the canvas point at the panel's top-left, and the zoom. */
export interface View {
  x: number;
  y: number;
  zoom: number;
}

const ZOOM_MIN = 0.05;
const ZOOM_MAX = 4;

export const isDesignCanvas = (path: string) => /\.design\.json$/i.test(path);

const canvasUrl = (threadId: string, path: string) => `/api/threads/${encodeURIComponent(threadId)}/canvas?path=${encodeURIComponent(path)}`;

async function answer(response: Response): Promise<Canvas> {
  const body = (await response.json().catch(() => null)) as (Canvas & { error?: string }) | null;
  if (!response.ok || !body) throw new Error(body?.error ?? `HTTP ${response.status}`);
  return body;
}

export async function readCanvas(threadId: string, path: string): Promise<Canvas> {
  return answer(await fetch(canvasUrl(threadId, path)));
}

/** Saves what the person did: boards moved or resized (by id), and the notes as they now are. */
export async function placeOnCanvas(
  threadId: string,
  path: string,
  boards: Record<string, Partial<Pick<CanvasBoard, "x" | "y" | "width" | "height">>>,
  notes?: CanvasNote[],
): Promise<Canvas> {
  return answer(
    await fetch(canvasUrl(threadId, path), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ boards, notes }),
    }),
  );
}

const clampZoom = (zoom: number) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoom));

/** The view after zooming by `factor` around a point of the panel, which stays where it is. */
export function zoomAt(view: View, factor: number, px: number, py: number): View {
  const zoom = clampZoom(view.zoom * factor);
  const cx = view.x + px / view.zoom;
  const cy = view.y + py / view.zoom;
  return { zoom, x: cx - px / zoom, y: cy - py / zoom };
}

/** The view that shows every board and note in a panel of this size, never above 100%. */
export function fitView(canvas: Canvas, width: number, height: number, margin = 48): View {
  const boxes = [
    ...canvas.boards.map((b) => ({ x: b.x, y: b.y - 28, w: b.width, h: b.height + 28 })),
    ...canvas.notes.map((n) => ({ x: n.x, y: n.y, w: n.width, h: 120 })),
  ];
  if (!boxes.length || width <= 0 || height <= 0) return { x: -margin, y: -margin, zoom: 1 };
  const left = Math.min(...boxes.map((b) => b.x));
  const top = Math.min(...boxes.map((b) => b.y));
  const right = Math.max(...boxes.map((b) => b.x + b.w));
  const bottom = Math.max(...boxes.map((b) => b.y + b.h));
  const zoom = clampZoom(Math.min(1, (width - 2 * margin) / (right - left), (height - 2 * margin) / (bottom - top)));
  return {
    zoom,
    x: left - (width / zoom - (right - left)) / 2,
    y: top - (height / zoom - (bottom - top)) / 2,
  };
}
