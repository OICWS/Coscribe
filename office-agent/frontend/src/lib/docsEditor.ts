import type { JSONContent } from "@tiptap/core";
import type { Node as PMNode } from "@tiptap/pm/model";

/** The Word file as the server gives it (`GET /api/threads/{id}/docs/blocks`, decision 0019). */
interface Run {
  t: string;
  b?: true;
  i?: true;
  u?: true;
  link?: string;
}

/** A picture's width as a percent of the text width, and what it shows in words. */
export interface PictureSetting {
  width: number;
  alt: string;
}

export type Block =
  | { id?: string; kind: "paragraph" | "title" | "quote"; style?: string; runs: Run[] }
  | { id?: string; kind: "heading"; level: number; runs: Run[] }
  | { id?: string; kind: "bullet" | "number"; level: number; runs: Run[] }
  | { id?: string; kind: "table"; header: boolean; rows: Run[][][] }
  | { id?: string; kind: "locked"; what?: string; text?: string; images?: string[]; picture?: PictureSetting }
  | { id?: string; kind: "image"; data: string }
  | { id?: string; kind: "divider" }
  | { id?: string; kind: "pagebreak" };

export interface DocBlocks {
  version: string;
  blocks: Block[];
}

/** A save over a file that changed after the editor read it. */
export class DocChangedError extends Error {}

const url = (threadId: string) => `/api/threads/${encodeURIComponent(threadId)}/docs/blocks`;

export async function getDocBlocks(threadId: string, path: string): Promise<DocBlocks> {
  const response = await fetch(`${url(threadId)}?path=${encodeURIComponent(path)}`);
  if (!response.ok) throw new Error(((await response.json().catch(() => null)) as { error?: string } | null)?.error ?? `HTTP ${response.status}`);
  return (await response.json()) as DocBlocks;
}

export async function saveDocBlocks(threadId: string, path: string, version: string, blocks: Block[]): Promise<DocBlocks> {
  const response = await fetch(url(threadId), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, version, blocks }),
  });
  if (response.ok) return (await response.json()) as DocBlocks;
  const failure = (await response.json().catch(() => null)) as { error?: string } | null;
  if (response.status === 409) throw new DocChangedError(failure?.error);
  throw new Error(failure?.error ?? `HTTP ${response.status}`);
}

/** Puts a version the editor once held back over the one it holds. */
export async function restoreDocVersion(threadId: string, path: string, version: string, to: string): Promise<DocBlocks> {
  const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}/docs/restore`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, version, to }),
  });
  if (response.ok) return (await response.json()) as DocBlocks;
  const failure = (await response.json().catch(() => null)) as { error?: string } | null;
  throw new Error(failure?.error ?? `HTTP ${response.status}`);
}

/** The message "Ask coscribe" sends for selected words: the file, then the words quoted. */
export function askAboutWords(file: string, words: string): string {
  return `Question about ${file}:\n${words.split("\n").map((line) => `> ${line}`).join("\n")}`;
}

// -- Blocks to the editor's document -------------------------------------------------------------

const MAX_LEVEL = 3;

function inline(runs: Run[]): JSONContent[] {
  const nodes: JSONContent[] = [];
  for (const run of runs) {
    const marks: NonNullable<JSONContent["marks"]> = [];
    if (run.b) marks.push({ type: "bold" });
    if (run.i) marks.push({ type: "italic" });
    if (run.u) marks.push({ type: "underline" });
    if (run.link) marks.push({ type: "link", attrs: { href: run.link } });
    run.t.split("\n").forEach((piece, index) => {
      if (index > 0) nodes.push({ type: "hardBreak" });
      if (piece) nodes.push({ type: "text", text: piece, ...(marks.length ? { marks } : {}) });
    });
  }
  return nodes;
}

const withContent = (node: JSONContent, content: JSONContent[]): JSONContent => (content.length ? { ...node, content } : node);
const identified = (id?: string) => (id ? { blockId: id } : {});
const paragraph = (runs: Run[], id?: string): JSONContent => withContent({ type: "paragraph", attrs: identified(id) }, inline(runs));

type ListBlock = Extract<Block, { kind: "bullet" | "number" }>;

/** Consecutive list items, which the file keeps flat with a level, become nested lists. */
function lists(items: ListBlock[]): JSONContent[] {
  const roots: JSONContent[] = [];
  const open: JSONContent[] = []; // open[d] is the list being filled at depth d
  for (const item of items) {
    const depth = Math.min(Math.max(item.level, 1) - 1, open.length);
    open.length = Math.min(open.length, depth + 1);
    const type = item.kind === "bullet" ? "bulletList" : "orderedList";
    let list = open[depth];
    if (!list || list.type !== type) {
      list = { type, content: [] };
      const parent = open[depth - 1];
      const holder = parent?.content?.[parent.content.length - 1];
      if (holder) holder.content = [...(holder.content ?? []), list];
      else roots.push(list);
      open[depth] = list;
      open.length = depth + 1;
    }
    list.content = [...(list.content ?? []), { type: "listItem", attrs: identified(item.id), content: [paragraph(item.runs)] }];
  }
  return roots;
}

/** Where a picture of the document is read from; the version in the url makes a changed file a new picture. */
export const docImageUrl = (threadId: string, path: string, version: string) => (rid: string) =>
  `/api/threads/${encodeURIComponent(threadId)}/docs/image?path=${encodeURIComponent(path)}&rid=${encodeURIComponent(rid)}&v=${version}`;

export function blocksToDoc(blocks: Block[], imageUrl: (rid: string) => string = (rid) => rid): JSONContent {
  const content: JSONContent[] = [];
  for (let at = 0; at < blocks.length; at += 1) {
    const block = blocks[at];
    if (block.kind === "bullet" || block.kind === "number") {
      let end = at;
      while (end + 1 < blocks.length && (blocks[end + 1].kind === "bullet" || blocks[end + 1].kind === "number")) end += 1;
      content.push(...lists(blocks.slice(at, end + 1) as ListBlock[]));
      at = end;
    } else if (block.kind === "heading") {
      content.push(withContent({ type: "heading", attrs: { level: block.level, ...identified(block.id) } }, inline(block.runs)));
    } else if (block.kind === "title") {
      content.push(withContent({ type: "title", attrs: identified(block.id) }, inline(block.runs)));
    } else if (block.kind === "quote") {
      content.push({ type: "blockquote", attrs: identified(block.id), content: [paragraph(block.runs)] });
    } else if (block.kind === "table") {
      const rows = block.rows.map((row, r) => ({
        type: "tableRow",
        content: row.map((cell) => ({ type: block.header && r === 0 ? "tableHeader" : "tableCell", content: [paragraph(cell)] })),
      }));
      content.push({ type: "table", attrs: identified(block.id), content: rows });
    } else if (block.kind === "locked") {
      content.push({ type: "lockedBlock", attrs: { what: block.what ?? "", text: block.text ?? "", images: (block.images ?? []).map(imageUrl), picture: block.picture ?? null, ...identified(block.id) } });
    } else if (block.kind === "divider" || block.kind === "pagebreak") {
      content.push({ type: block.kind === "divider" ? "divider" : "pageBreak", attrs: identified(block.id) });
    } else if (block.kind !== "image") {
      content.push(paragraph(block.runs, block.id));
    }
  }
  return { type: "doc", content: content.length ? content : [{ type: "paragraph" }] };
}

// -- The editor's document to blocks ------------------------------------------------------------

/** Where the node that carries a block's id sits in the document; `pos` is -1 for a block that has no
 * node of its own (a second paragraph of a list item). */
interface Slot {
  pos: number;
  type: string;
}

const MARKS: [string, "b" | "i" | "u"][] = [
  ["bold", "b"],
  ["italic", "i"],
  ["underline", "u"],
];

function runs(node: PMNode): Run[] {
  const found: Run[] = [];
  const add = (t: string, marks: Omit<Run, "t">) => {
    const last = found[found.length - 1];
    if (last && JSON.stringify({ ...last, t: "" }) === JSON.stringify({ ...marks, t: "" })) last.t += t;
    else found.push({ t, ...marks });
  };
  node.forEach((child) => {
    if (child.type.name === "hardBreak") return add("\n", {});
    if (!child.isText || !child.text) return;
    const marks: Omit<Run, "t"> = {};
    for (const [name, key] of MARKS) if (child.marks.some((m) => m.type.name === name)) marks[key] = true;
    const link = child.marks.find((m) => m.type.name === "link");
    if (link) marks.link = String(link.attrs.href);
    add(child.text, marks);
  });
  return found;
}

const idOf = (node: PMNode): string | undefined => (typeof node.attrs.blockId === "string" ? node.attrs.blockId : undefined);

export function docToBlocks(doc: PMNode): { blocks: Block[]; slots: Slot[] } {
  const blocks: Block[] = [];
  const slots: Slot[] = [];
  const emit = (block: Block, node: PMNode | null, pos: number) => {
    blocks.push(block);
    slots.push(node ? { pos, type: node.type.name } : { pos: -1, type: "" });
  };
  const listItems = (list: PMNode, listPos: number, depth: number) => {
    const kind = list.type.name === "bulletList" ? "bullet" : "number";
    const level = Math.min(depth + 1, MAX_LEVEL);
    list.forEach((item, offset) => {
      const pos = listPos + 1 + offset;
      let first = true;
      item.forEach((part, partOffset) => {
        if (part.type.name === "paragraph") {
          emit({ id: first ? idOf(item) : undefined, kind, level, runs: runs(part) }, first ? item : null, pos);
          first = false;
        } else listItems(part, pos + 1 + partOffset, depth + 1);
      });
    });
  };
  doc.forEach((node, offset) => {
    const name = node.type.name;
    if (name === "heading") emit({ id: idOf(node), kind: "heading", level: Number(node.attrs.level), runs: runs(node) }, node, offset);
    else if (name === "title") emit({ id: idOf(node), kind: "title", runs: runs(node) }, node, offset);
    else if (name === "blockquote") {
      node.forEach((part, index) => emit({ id: index === 0 ? idOf(node) : undefined, kind: "quote", runs: runs(part) }, index === 0 ? node : null, offset));
    } else if (name === "bulletList" || name === "orderedList") listItems(node, offset, 0);
    else if (name === "table") {
      const rows: Run[][][] = [];
      let header = true;
      node.forEach((row, r) => {
        const cells: Run[][] = [];
        row.forEach((cell) => {
          if (r === 0 && cell.type.name !== "tableHeader") header = false;
          cells.push(runs(cell.firstChild ?? cell));
        });
        rows.push(cells);
      });
      emit({ id: idOf(node), kind: "table", header, rows }, node, offset);
    } else if (name === "divider" || name === "pageBreak") {
      emit({ id: idOf(node), kind: name === "divider" ? "divider" : "pagebreak" }, node, offset);
    } else if (name === "lockedBlock") {
      const upload = String(node.attrs.upload ?? "");
      const picture = node.attrs.picture as PictureSetting | null;
      emit(upload ? { kind: "image", data: upload } : { id: idOf(node), kind: "locked", ...(picture ? { picture } : {}) }, node, offset);
    }
    else emit({ id: idOf(node), kind: "paragraph", runs: runs(node) }, node, offset);
  });
  return { blocks, slots };
}
