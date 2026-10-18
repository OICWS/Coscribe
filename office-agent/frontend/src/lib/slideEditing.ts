/** One slide as the editor reads and saves it (`/api/threads/{id}/slides/{index}/parts|source`). */
import type { Box } from "./slideSource";

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
