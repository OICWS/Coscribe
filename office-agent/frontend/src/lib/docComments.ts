import type { CommentReply } from "./slideComments";

/** A Doc's comment as the server gives it (`/api/threads/{id}/doc/comments`, decision 0025). */
export interface DocComment {
  id: string;
  text: string;
  /** The words of the block it was made on, when it was made on some. */
  quote: string;
  author: string;
  created: string;
  sent: boolean;
  resolved: boolean;
  replies: CommentReply[];
  /** The block it sits on now; null when the block's text is gone. */
  block: number | null;
  detached: boolean;
}

const base = (threadId: string) => `/api/threads/${encodeURIComponent(threadId)}/doc/comments`;
const one = (threadId: string, id: string) => `${base(threadId)}/${encodeURIComponent(id)}`;

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { error?: string };
    throw new Error(body.error ?? `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

const send = (method: string, url: string, body: unknown) => fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const getDocComments = async (threadId: string, path: string) => json<DocComment[]>(await fetch(`${base(threadId)}?path=${encodeURIComponent(path)}`));

export const addDocComment = async (threadId: string, comment: { path: string; block: number; text: string; quote: string; sent: boolean }) =>
  json<DocComment>(await send("POST", base(threadId), comment));

export const replyToDocComment = async (threadId: string, path: string, id: string, text: string, fromCoscribe = false) =>
  json<CommentReply>(await send("POST", `${one(threadId, id)}/replies`, { path, text, from_coscribe: fromCoscribe }));

export const resolveDocComment = async (threadId: string, path: string, id: string, resolved: boolean) => json<unknown>(await send("POST", one(threadId, id), { path, resolved }));

export const markDocCommentSent = async (threadId: string, path: string, id: string) => json<unknown>(await send("POST", one(threadId, id), { path, sent: true }));

export const editDocComment = async (threadId: string, path: string, id: string, text: string) => json<unknown>(await send("PUT", one(threadId, id), { path, text }));

export const deleteDocComment = async (threadId: string, path: string, id: string) => json<unknown>(await fetch(`${one(threadId, id)}?path=${encodeURIComponent(path)}`, { method: "DELETE" }));

const quoted = (text: string) =>
  text
    .split("\n")
    .map((line) => `> ${line}`)
    .join("\n");

const SNIPPET = 80;
const snippet = (text: string) => (text.length > SNIPPET ? `${text.slice(0, SNIPPET - 1)}…` : text);

/** What one comment says to coscribe: where it is (the words it is on, else the start of the block) so
 * the model can find the place to change, then the words. */
function entry(comment: { quote: string; blockText: string; text: string }): string {
  const on = comment.quote || snippet(comment.blockText.replace(/\s+/g, " "));
  return `On "${on}":\n${quoted(comment.text)}`;
}

/** The message that sends comments to coscribe: one comment, or several in one go. */
export function docCommentsMessage(file: string, comments: { quote: string; blockText: string; text: string }[]): string {
  if (comments.length === 1) return `Comment on ${file}, ${entry(comments[0])}`;
  return `Comments on ${file}:\n\n${comments.map((c, i) => `${i + 1}. ${entry(c)}`).join("\n\n")}`;
}
