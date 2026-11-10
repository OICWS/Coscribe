/** The Files panel's view of a conversation's folders: what `/api/threads/{id}/workspace` lists,
 * which way each kind of file is shown, and the open tabs. Pure, apart from the fetches. */

export interface WorkspaceRoot {
  name: string;
  path: string;
}

export interface WorkspaceEntry {
  name: string;
  dir: boolean;
  size: number | null;
  /** A folder of tools' own files (node_modules, caches): shown greyed, never searched. */
  dim?: boolean;
  /** Only in search results: the path under the folder. */
  path?: string;
}

interface Listing {
  entries: WorkspaceEntry[];
  truncated: boolean;
}

/** A file in one of the conversation's folders: which folder (by its place in the list) and the
 * path under it, with forward slashes. */
export interface FileRef {
  root: number;
  path: string;
}

const base = (threadId: string) => `/api/threads/${encodeURIComponent(threadId)}/workspace`;
const encodePath = (path: string) => path.split("/").map(encodeURIComponent).join("/");

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  const body = (await res.json().catch(() => ({}))) as T & { error?: string };
  if (!res.ok) throw new Error(body.error ?? `${res.status} ${res.statusText}`);
  return body;
}

export const getRoots = (threadId: string) => getJson<{ roots: WorkspaceRoot[] }>(base(threadId)).then((r) => r.roots);

export const listFolder = (threadId: string, root: number, path: string) =>
  getJson<Listing>(`${base(threadId)}/${root}/list?path=${encodeURIComponent(path)}`);

export const searchFiles = (threadId: string, root: number, query: string) =>
  getJson<Listing>(`${base(threadId)}/${root}/search?q=${encodeURIComponent(query)}`);

/** The file as it is on disk; relative links in a page served from here reach its neighbours. */
export const rawUrl = (threadId: string, ref: FileRef) => `${base(threadId)}/${ref.root}/raw/${encodePath(ref.path)}`;

/** The path the rest of the app names a file by: under the main folder relative, elsewhere whole. */
export function appPath(roots: readonly WorkspaceRoot[], ref: FileRef): string {
  if (ref.root === 0) return ref.path;
  const folder = roots[ref.root]?.path ?? "";
  const sep = folder.includes("\\") ? "\\" : "/";
  return `${folder.replace(/[\\/]+$/, "")}${sep}${ref.path.split("/").join(sep)}`;
}

export const sameRef = (a: FileRef | null, b: FileRef | null) => !!a && !!b && a.root === b.root && a.path === b.path;
export const refKey = (ref: FileRef) => `${ref.root}:${ref.path}`;
export const baseName = (path: string) => path.slice(path.lastIndexOf("/") + 1);

/** How a file is shown. `rendered` kinds also have their source a click away. */
export type FileKind = "markdown" | "html" | "svg" | "csv" | "image" | "pdf" | "office" | "text" | "binary";

const IMAGE = /\.(png|jpe?g|gif|webp|bmp|ico|avif)$/i;
const OFFICE = /\.(docx?|xlsx?|xlsm|pptx?|odt|ods|odp)$/i;
const BINARY = /\.(zip|7z|rar|gz|tgz|exe|dll|msi|bin|so|dylib|pyc|class|jar|mp3|mp4|mov|avi|wav|woff2?|ttf|otf|sqlite|db)$/i;

export function fileKind(path: string): FileKind {
  if (/\.(md|markdown)$/i.test(path)) return "markdown";
  if (/\.html?$/i.test(path)) return "html";
  if (/\.svg$/i.test(path)) return "svg";
  if (/\.(csv|tsv)$/i.test(path)) return "csv";
  if (IMAGE.test(path)) return "image";
  if (/\.pdf$/i.test(path)) return "pdf";
  if (OFFICE.test(path)) return "office";
  if (BINARY.test(path)) return "binary";
  return "text";
}

/** Kinds shown drawn by default, with a switch to their source. */
export const hasSource = (kind: FileKind) => kind === "markdown" || kind === "html" || kind === "svg" || kind === "csv";

/** Kinds read as text, for the code view or a table. */
export const readsText = (kind: FileKind) => kind === "text" || hasSource(kind);

/** Text over this is not loaded into the code view: offered to open in its own program instead. */
export const MAX_TEXT_BYTES = 2 * 1024 * 1024;

/** A file whose first bytes hold a NUL is not text, whatever its name says. */
export const looksBinary = (text: string) => text.slice(0, 8000).includes("\u0000");

/** Fields of one CSV or TSV line, with quoted fields that may hold the separator or a doubled quote. */
export function splitCsv(text: string, separator: string, maxRows = 1000): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length && rows.length < maxRows; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"' && field === "") quoted = true;
    else if (ch === separator) {
      row.push(field);
      field = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else field += ch;
  }
  if ((field || row.length) && rows.length < maxRows) rows.push([...row, field]);
  return rows;
}

/** The open tabs: at most one preview tab (italic, replaced by the next file opened) and any
 * number kept with the pin. */
export interface Tabs {
  open: { ref: FileRef; kept: boolean }[];
  active: FileRef | null;
}

export const NO_TABS: Tabs = { open: [], active: null };

export function openTab(tabs: Tabs, ref: FileRef, keep = false): Tabs {
  const existing = tabs.open.find((t) => sameRef(t.ref, ref));
  if (existing) {
    const open = keep ? tabs.open.map((t) => (t === existing ? { ...t, kept: true } : t)) : tabs.open;
    return { open, active: ref };
  }
  const previewAt = tabs.open.findIndex((t) => !t.kept);
  const tab = { ref, kept: keep };
  const open = previewAt >= 0 && !keep ? tabs.open.map((t, i) => (i === previewAt ? tab : t)) : [...tabs.open, tab];
  return { open, active: ref };
}

export function closeTab(tabs: Tabs, ref: FileRef): Tabs {
  const index = tabs.open.findIndex((t) => sameRef(t.ref, ref));
  if (index < 0) return tabs;
  const open = tabs.open.filter((_, i) => i !== index);
  if (!sameRef(tabs.active, ref)) return { open, active: tabs.active };
  const next = open[Math.min(index, open.length - 1)];
  return { open, active: next ? next.ref : null };
}

export const keepTab = (tabs: Tabs, ref: FileRef): Tabs => ({
  ...tabs,
  open: tabs.open.map((t) => (sameRef(t.ref, ref) ? { ...t, kept: !t.kept } : t)),
});
