type DocxView = "final" | "original";

const base = (threadId: string, path: string, suffix = "") =>
  `/api/threads/${encodeURIComponent(threadId)}/docx-review${suffix}?path=${encodeURIComponent(path)}`;

async function ok(res: Response): Promise<Response> {
  if (res.ok) return res;
  const body = (await res.json().catch(() => null)) as { error?: string } | null;
  throw new Error(body?.error ?? `The server answered ${res.status}`);
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
