/** A Doc as the server gives it (`/api/threads/{id}/doc/blocks`, decision 0025). */
export interface DocBlock {
  index: number;
  kind: string;
  text: string;
}

export interface DocRead {
  version: string;
  title: string;
  blocks: DocBlock[];
}

export type DocEdit =
  | { op: "replace"; index: number; expected: string; text: string }
  | { op: "insert"; after: number; text: string }
  | { op: "delete"; index: number; expected: string };

/** A Markdown file that is not a Doc: it has no `coscribe: doc` in its front matter. */
export class NotADocError extends Error {}

/** A save over a file that changed after the editor read it. */
export class DocChangedError extends Error {}

const base = (threadId: string) => `/api/threads/${encodeURIComponent(threadId)}/doc`;

async function failure(response: Response): Promise<Error> {
  const body = (await response.json().catch(() => null)) as { error?: string; changed?: boolean } | null;
  const message = body?.error ?? `HTTP ${response.status}`;
  return response.status === 409 ? new DocChangedError(message) : response.status === 404 ? new NotADocError(message) : new Error(message);
}

export async function getDoc(threadId: string, path: string): Promise<DocRead> {
  const response = await fetch(`${base(threadId)}/blocks?path=${encodeURIComponent(path)}`);
  if (!response.ok) throw await failure(response);
  return (await response.json()) as DocRead;
}

export async function saveDoc(threadId: string, path: string, version: string, edits: DocEdit[]): Promise<DocRead> {
  const response = await fetch(`${base(threadId)}/blocks`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, version, edits }),
  });
  if (!response.ok) throw await failure(response);
  return (await response.json()) as DocRead;
}

/** The file as it was at `to`, taken over the file at `version`: one step of undo or redo for a
 * change made behind the editor's back. */
export async function restoreDoc(threadId: string, path: string, version: string, to: string): Promise<DocRead> {
  const response = await fetch(`${base(threadId)}/restore`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, version, to }),
  });
  if (!response.ok) throw await failure(response);
  return (await response.json()) as DocRead;
}
