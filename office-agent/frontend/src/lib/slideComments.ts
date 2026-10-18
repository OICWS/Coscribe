/** A slide's comments as the server keeps them (`/api/threads/{id}/slides/comments`). */

export interface SlideElement {
  id: string;
  /** `Title "Q3 review"`, `Text "896k"`, `Chart`, ... */
  label: string;
  /** x, y, width, height as fractions of the slide. */
  box: [number, number, number, number];
}

export interface CommentReply {
  author: string;
  text: string;
  created: string;
}

export interface SlideComment {
  id: string;
  /** The slide's page name without its suffix. */
  slide: string;
  x: number;
  y: number;
  element: string;
  text: string;
  author: string;
  created: string;
  sent: boolean;
  resolved: boolean;
  replies: CommentReply[];
}

/** Where coscribe's answer to a comment goes once its turn ends. */
export interface CommentLink {
  path: string;
  commentId: string;
}

const base = (threadId: string) => `/api/threads/${encodeURIComponent(threadId)}/slides/comments`;

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { error?: string };
    throw new Error(body.error ?? `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

const post = (url: string, body: unknown) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const getComments = async (threadId: string, path: string) =>
  json<SlideComment[]>(await fetch(`${base(threadId)}?path=${encodeURIComponent(path)}`));

export const addComment = async (
  threadId: string,
  comment: { path: string; slide: string; x: number; y: number; element: string; text: string; sent: boolean },
) => json<SlideComment>(await post(base(threadId), comment));

export const replyToComment = async (threadId: string, path: string, id: string, text: string, fromCoscribe = false) =>
  json<CommentReply>(await post(`${base(threadId)}/${encodeURIComponent(id)}/replies`, { path, text, from_coscribe: fromCoscribe }));

export const resolveComment = async (threadId: string, path: string, id: string, resolved: boolean) =>
  json<{ resolved: boolean }>(await post(`${base(threadId)}/${encodeURIComponent(id)}`, { path, resolved }));

export const deleteComment = async (threadId: string, path: string, id: string) =>
  json<{ deleted: string }>(
    await fetch(`${base(threadId)}/${encodeURIComponent(id)}?path=${encodeURIComponent(path)}`, { method: "DELETE" }),
  );

/** The element under a point (fractions of the slide): the smallest box that holds it, so a
 * click inside a card picks the words, not the card behind them. */
export function elementAt(elements: SlideElement[], x: number, y: number): SlideElement | null {
  let best: SlideElement | null = null;
  for (const element of elements) {
    const [left, top, width, height] = element.box;
    // Lines and rules are a pixel thick; give them a little room to be hit.
    const slackX = width < 0.01 ? 0.005 : 0;
    const slackY = height < 0.01 ? 0.005 : 0;
    if (x < left - slackX || x > left + width + slackX || y < top - slackY || y > top + height + slackY) continue;
    if (!best || width * height < best.box[2] * best.box[3]) best = element;
  }
  return best;
}

/** Where a comment sits, as the panel and the message say it: "Slide 2 › Title "…"". */
export const commentPlace = (slideNumber: number, element: string) => `Slide ${slideNumber} › ${element || "the slide"}`;

/** The message a comment sends to coscribe: what it is on, so the model can find the page to
 * change, then the words. */
export function commentMessage(deck: string, slideNumber: number, page: string, element: string, text: string): string {
  const quoted = text
    .split("\n")
    .map((line) => `> ${line}`)
    .join("\n");
  return `Comment on ${deck}, ${commentPlace(slideNumber, element)} (page ${page}):\n${quoted}`;
}
