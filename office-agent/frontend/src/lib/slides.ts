/** A deck built from pages, as the server reads it (`GET /api/threads/{id}/slides`). */
export interface SlideInfo {
  name: string;
  /** "page": an unedited SVG page, drawn as an image. "section": an edited slide. */
  kind: "page" | "section";
  notes: string;
  /** PowerPoint's name for the transition ("fade", "push", "morph", ...), or null. */
  transition: string | null;
  /** "#RRGGBB", or null when the slide has no background of its own. */
  background: string | null;
}

export interface SlideDeck {
  title: string;
  folder: string;
  /** The .pptx or a page changed since the last build: what is shown may differ from the file. */
  changed: boolean;
  slides: SlideInfo[];
}

/** The slide's own size in the panel's units: 100% zoom draws it 1920 pixels wide. */
export const SLIDE_WIDTH = 1920;
export const SLIDE_HEIGHT = 1080;
export const ZOOM_STEPS = [0.25, 0.5, 0.75, 1, 1.5, 2];
const MIN_ZOOM = 0.05;
const MAX_ZOOM = 2;

export const isPptx = (path: string) => /\.pptx$/i.test(path);

export class DeckNotBuilt extends Error {}

const base = (threadId: string) => `/api/threads/${encodeURIComponent(threadId)}/slides`;

export async function getSlideDeck(threadId: string, path: string): Promise<SlideDeck> {
  const response = await fetch(`${base(threadId)}?path=${encodeURIComponent(path)}`);
  if (response.status === 409) throw new DeckNotBuilt();
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as {
      error?: string;
    };
    throw new Error(body.error ?? `HTTP ${response.status}`);
  }
  return (await response.json()) as SlideDeck;
}

/** The slide as one SVG with nothing outside it; `version` changes when the deck is rebuilt. */
export function slideImageUrl(threadId: string, path: string, index: number, version: string): string {
  return `${base(threadId)}/${index}/svg?path=${encodeURIComponent(path)}&v=${encodeURIComponent(version)}`;
}

/** The zoom that fits a slide inside `width` × `height`. */
export function fitZoom(width: number, height: number): number {
  const zoom = Math.min(width / SLIDE_WIDTH, height / SLIDE_HEIGHT);
  return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom));
}

/** The next preset zoom past `zoom` in `direction`, or `zoom` when there is none. */
export function stepZoom(zoom: number, direction: 1 | -1): number {
  const next = direction > 0 ? ZOOM_STEPS.find((step) => step > zoom + 1e-6) : [...ZOOM_STEPS].reverse().find((step) => step < zoom - 1e-6);
  return next ?? zoom;
}

export const zoomLabel = (zoom: number) => `${Math.round(zoom * 100)}%`;

/** PowerPoint's transition names as the properties panel says them. */
export function transitionLabel(name: string | null): string {
  if (!name) return "None";
  if (name === "morph") return "Magic move";
  return name.charAt(0).toUpperCase() + name.slice(1);
}

/** What the Download menu offers; "png" is the current slide, drawn here. */
export type SlideExport = "pdf" | "html" | "png" | "pptx" | "pptx-basic";

/** The file for a download: from the server, or for "png" the slide `index` drawn at 1920 × 1080. */
export async function slideExport(
  threadId: string,
  path: string,
  kind: SlideExport,
  index: number,
  slideUrl: string,
): Promise<{ blob: Blob; name: string }> {
  const stem = (path.split(/[\\/]/).pop() ?? path).replace(/\.pptx$/i, "");
  if (kind === "png") return { blob: await drawSlide(slideUrl), name: `${stem} - slide ${index + 1}.png` };
  const url =
    kind === "pptx"
      ? `/api/threads/${encodeURIComponent(threadId)}/files/download?path=${encodeURIComponent(path)}`
      : `${base(threadId)}/export?path=${encodeURIComponent(path)}&format=${kind}`;
  const response = await fetch(url);
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { error?: string };
    throw new Error(body.error ?? `HTTP ${response.status}`);
  }
  const name = { pdf: ".pdf", html: ".html", pptx: ".pptx", "pptx-basic": " (basic fonts).pptx" }[kind];
  return { blob: await response.blob(), name: `${stem}${name}` };
}

async function drawSlide(url: string): Promise<Blob> {
  const image = new Image();
  image.src = url;
  await image.decode();
  const canvas = document.createElement("canvas");
  canvas.width = SLIDE_WIDTH;
  canvas.height = SLIDE_HEIGHT;
  canvas.getContext("2d")?.drawImage(image, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT);
  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("The slide could not be drawn"))), "image/png"),
  );
}

/** Hands `blob` to the browser (or the desktop app) as a file named `name`. */
export function saveBlob(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
