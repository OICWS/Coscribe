/** A Word file's review as the server reads it (`GET /api/threads/{id}/docx-review`). */

export interface DocxChange {
  id: string;
  kind: "insert" | "delete";
  author: string;
  date: string;
  text: string;
  under: string;
}

export interface DocxReply {
  id: string;
  author: string;
  initials: string;
  date: string;
  text: string;
  done: boolean;
}

export interface DocxComment extends DocxReply {
  anchor: string;
  replies: DocxReply[];
}

export interface DocxReview {
  path: string;
  changes: DocxChange[];
  other_changes: number;
  comments: DocxComment[];
}

export type DocxView = "review" | "final" | "original";

const base = (threadId: string, path: string, suffix = "") =>
  `/api/threads/${encodeURIComponent(threadId)}/docx-review${suffix}?path=${encodeURIComponent(path)}`;

async function ok(res: Response): Promise<Response> {
  if (res.ok) return res;
  const body = (await res.json().catch(() => null)) as { error?: string } | null;
  throw new Error(body?.error ?? `The server answered ${res.status}`);
}

export async function getDocxReview(threadId: string, path: string): Promise<DocxReview> {
  return (await ok(await fetch(base(threadId, path)))).json() as Promise<DocxReview>;
}

/** The file's bytes for `view`: the Original view is a copy with every change rejected. */
export async function getDocxBytes(threadId: string, path: string, view: DocxView): Promise<ArrayBuffer> {
  const url =
    view === "original"
      ? base(threadId, path, "/original")
      : `/api/threads/${encodeURIComponent(threadId)}/files/download?path=${encodeURIComponent(path)}`;
  return (await ok(await fetch(url))).arrayBuffer();
}

export const isDocx = (path: string) => /\.docx$/i.test(path);

/** Where each comment card sits in the rail, given the height of its words on
 * the page (`anchor`) and its own height, top to bottom. Cards keep level with
 * their words when there is room; the active one always does, and the others
 * make way above and below it. */
export function stackCards(
  cards: { id: string; anchor: number; height: number }[],
  activeId: string | null,
  gap: number,
): Record<string, number> {
  const tops: Record<string, number> = {};
  const at = cards.findIndex((c) => c.id === activeId);
  const pivot = at >= 0 ? at : 0;
  let floor = at >= 0 ? cards[pivot].anchor : -Infinity;
  for (let i = pivot; i < cards.length; i++) {
    tops[cards[i].id] = Math.max(cards[i].anchor, floor);
    floor = tops[cards[i].id] + cards[i].height + gap;
  }
  let ceiling = at >= 0 ? cards[pivot].anchor - gap : Infinity;
  for (let i = pivot - 1; i >= 0; i--) {
    tops[cards[i].id] = Math.min(cards[i].anchor, ceiling - cards[i].height);
    ceiling = tops[cards[i].id] - gap;
  }
  return tops;
}
