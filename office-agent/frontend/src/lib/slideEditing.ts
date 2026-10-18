/** One slide as the editor reads and saves it (`/api/threads/{id}/slides/{index}/parts|source`). */
import { parseSection, writeSection, type Box } from "./slideSource";

export interface SlidePart {
  kind: "text" | "drawing" | "refused";
  box: Box | null;
  /** An SVG data URI of the element alone, `PICTURE_MARGIN` px past its box; null for text. */
  picture: string | null;
}

export interface SlideParts {
  name: string;
  /** "page" until the first save turns the SVG page into a section. */
  kind: "page" | "section";
  version: string;
  source: string;
  parts: SlidePart[];
}

export interface SavedSlide {
  name: string;
  version: string;
  /** What the build found on the slide: text that no longer fits, ... */
  problems: string[];
}

/** Room the server leaves around an element's box in its picture. */
export const PICTURE_MARGIN = 24;

/** A save the server refused because the slide or the .pptx changed meanwhile. */
export class SlideChangedError extends Error {
  readonly what: "slide" | "deck";
  constructor(message: string, what: "slide" | "deck") {
    super(message);
    this.what = what;
  }
}

const url = (threadId: string, index: number, end: string) =>
  `/api/threads/${encodeURIComponent(threadId)}/slides/${index}/${end}`;

async function json<T>(response: Response): Promise<T> {
  if (response.ok) return (await response.json()) as T;
  const body = (await response.json().catch(() => ({}))) as { error?: string; changed?: "slide" | "deck" };
  const message = body.error ?? `HTTP ${response.status}`;
  throw body.changed ? new SlideChangedError(message, body.changed) : new Error(message);
}

export const getSlideParts = async (threadId: string, path: string, index: number) =>
  json<SlideParts>(await fetch(`${url(threadId, index, "parts")}?path=${encodeURIComponent(path)}`));

export const saveSlideSource = async (threadId: string, path: string, index: number, source: string, version: string) =>
  json<SavedSlide>(
    await fetch(url(threadId, index, "source"), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, source, version }),
    }),
  );

/** Stores a picture in the deck's assets; returns its `src` and size in px. */
export async function uploadSlidePicture(threadId: string, path: string, file: File) {
  const form = new FormData();
  form.append("path", path);
  form.append("file", file);
  const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}/slides/assets`, { method: "POST", body: form });
  return json<{ src: string; width: number; height: number }>(response);
}

/** One change to a slide made outside the editor (its notes, transition, background): the
 * slide is read, changed and saved in one go. */
export async function editSlide(threadId: string, path: string, index: number, edit: (doc: Document) => void) {
  const read = await getSlideParts(threadId, path, index);
  const doc = parseSection(read.source);
  edit(doc);
  return saveSlideSource(threadId, path, index, writeSection(doc), read.version);
}

export type Arrange =
  | { action: "insert"; index: number; source: string }
  | { action: "duplicate" | "delete"; index: number }
  | { action: "move"; index: number; to: number };

/** A new, copied, moved or deleted slide; returns the index of the slide to show. */
export const arrangeSlides = async (threadId: string, path: string, change: Arrange) =>
  json<{ index: number }>(
    await fetch(`/api/threads/${encodeURIComponent(threadId)}/slides/arrange`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, ...change }),
    }),
  );
