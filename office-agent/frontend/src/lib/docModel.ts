import { Extension, Node, type AnyExtension, type JSONContent } from "@tiptap/core";
import { Image } from "@tiptap/extension-image";
import { TaskItem, TaskList } from "@tiptap/extension-list";
import { MarkdownManager } from "@tiptap/markdown";
import { Table, TableCell, TableHeader, TableRow } from "@tiptap/extension-table";
import type { Node as PMNode } from "@tiptap/pm/model";
import StarterKit from "@tiptap/starter-kit";
import type { DocBlock, DocEdit } from "./docFile";

/** Blocks the editor shows as their own markdown until a step gives them a view: the text stays
 * exactly as it is, and typing in it is typing the source. */
const RAW_KINDS = new Set(["html", "chart", "other"]);

export const CALLOUT_TYPES = ["NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION"] as const;
const CALLOUT_HEAD = /^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$/i;

const BLOCK_NODES = ["paragraph", "heading", "bulletList", "orderedList", "taskList", "blockquote", "table", "codeBlock", "horizontalRule", "rawBlock", "callout"];

/** Which block of the file a node is: the index the server gave it when the file was last read.
 * A node made since (Enter, a paste) has none, and is written as a new block. */
const BlockIndex = Extension.create({
  name: "blockIndex",
  addGlobalAttributes() {
    return [{ types: BLOCK_NODES, attributes: { blockIndex: { default: null, rendered: false, keepOnSplit: false } } }];
  },
});

const RawBlock = Node.create({
  name: "rawBlock",
  group: "block",
  content: "text*",
  marks: "",
  code: true,
  defining: true,
  addAttributes() {
    return { kind: { default: "other", rendered: false } };
  },
  parseHTML: () => [{ tag: "pre[data-raw]", preserveWhitespace: "full" }],
  renderHTML: ({ node }) => ["pre", { "data-raw": node.attrs.kind, class: "doc-raw" }, ["code", 0]],
});

/** A GitHub alert quote (`> [!NOTE]`): a coloured box of paragraphs with a kind. */
const Callout = Node.create({
  name: "callout",
  group: "block",
  content: "paragraph+",
  defining: true,
  addAttributes() {
    return { type: { default: "NOTE", rendered: false, parseHTML: (element: HTMLElement) => element.getAttribute("data-callout") ?? "NOTE" } };
  },
  parseHTML: () => [{ tag: "div[data-callout]" }],
  renderHTML: ({ node }) => ["div", { "data-callout": node.attrs.type, class: "doc-callout" }, 0],
});

/** What a Doc holds, and no more: what Markdown can say (decision 0025). */
export const docExtensions: AnyExtension[] = [
  StarterKit.configure({
    heading: { levels: [1, 2, 3] },
    // Markdown has no underline, and a link opens by a click only where the page is not being edited.
    underline: false,
    link: { openOnClick: false, autolink: false, protocols: ["http", "https", "mailto"] },
  }),
  TaskList,
  TaskItem.configure({ nested: true }),
  Image.configure({ inline: true }),
  Table.configure({ resizable: false }),
  TableRow,
  TableHeader,
  TableCell,
  BlockIndex,
  RawBlock,
  Callout,
];

let manager: MarkdownManager | null = null;
const markdown = () => (manager ??= new MarkdownManager({ extensions: docExtensions }));

/** What the editor read for a block, to tell later whether the person changed it. */
export interface Loaded {
  text: string;
  key: string;
}

/** A node without the index it carries: two nodes with the same key hold the same content. */
function nodeKey(node: PMNode | JSONContent): string {
  const json = "toJSON" in node ? (node.toJSON() as JSONContent) : node;
  return JSON.stringify(json, (key, value: unknown) => (key === "blockIndex" ? undefined : value));
}

/** A callout block as a node, or null when its body is more than paragraphs. */
function calloutNode(text: string, index: number): JSONContent | null {
  const [head, ...rest] = text.split("\n");
  const type = CALLOUT_HEAD.exec(head.trim())?.[1]?.toUpperCase();
  if (!type) return null;
  const body = rest.map((line) => line.replace(/^\s{0,3}>\s?/, "")).join("\n");
  const parsed = body.trim() ? (markdown().parse(body).content ?? []) : [{ type: "paragraph" }];
  if (!parsed.length || parsed.some((node) => node.type !== "paragraph")) return null;
  return { type: "callout", attrs: { type, blockIndex: index }, content: parsed };
}

function blockNode(block: DocBlock): JSONContent {
  const raw = (): JSONContent => ({ type: "rawBlock", attrs: { kind: block.kind, blockIndex: block.index }, content: [{ type: "text", text: block.text }] });
  if (RAW_KINDS.has(block.kind)) return raw();
  try {
    if (block.kind === "callout") return calloutNode(block.text, block.index) ?? raw();
    const parsed = markdown().parse(block.text).content ?? [];
    // Anything but one node is something the editor would not write back as it is.
    if (parsed.length !== 1) return raw();
    // A paragraph of one picture comes back as the picture alone.
    const node = parsed[0].type === "image" ? { type: "paragraph", content: [parsed[0]] } : parsed[0];
    return { ...node, attrs: { ...node.attrs, blockIndex: block.index } };
  } catch {
    return raw();
  }
}

/** The editor's content for a Doc's blocks. */
export function docContent(blocks: DocBlock[]): JSONContent {
  const nodes = blocks.map(blockNode);
  return { type: "doc", content: nodes.length ? nodes : [{ type: "paragraph" }] };
}

/** What each block held when it was read, taken from the editor's own nodes (the schema fills in
 * attributes the content did not name, so the key must come from the node, not the JSON it was made from). */
export function loadedOf(doc: PMNode, blocks: DocBlock[]): Map<number, Loaded> {
  return new Map(blocks.map((block, i) => [block.index, { text: block.text, key: nodeKey(doc.child(i)) }]));
}

/** A node's markdown with no blank line around it. */
export function nodeMarkdown(node: PMNode): string {
  if (node.type.name === "rawBlock") return node.textContent;
  if (node.type.name === "callout") {
    const body = node.content.content.map((paragraph) => nodeMarkdown(paragraph)).filter(Boolean).join("\n\n");
    return [`> [!${node.attrs.type as string}]`, ...(body ? body.split("\n").map((line) => (line ? `> ${line}` : ">")) : [])].join("\n");
  }
  return markdown().serialize({ type: "doc", content: [node.toJSON() as JSONContent] }).replace(/^\n+/, "").trimEnd();
}

/** Where a block of the file will be in the editor after a save: a node's position and its content. */
export interface Slot {
  pos: number;
  key: string;
}

/** The edits that bring the file to what the editor holds, and where each block of the saved file is.
 * Only a block the person changed is named: the rest of the file stays as it is, byte for byte. A node
 * that is not in the file's order (moved, or pasted twice) is a new block, and its old place is deleted. */
export function docEdits(doc: PMNode, loaded: Map<number, Loaded>): { edits: DocEdit[]; slots: Slot[] } {
  const edits: DocEdit[] = [];
  const slots: Slot[] = [];
  const kept = new Set<number>();
  const claimed = new Set<number>();
  let last = -1;
  let after = -1;
  let fresh: { after: number; texts: string[] } | null = null;
  const flush = () => {
    if (fresh) edits.push({ op: "insert", after: fresh.after, text: fresh.texts.join("\n\n") });
    fresh = null;
  };
  doc.forEach((node, pos) => {
    const index = node.attrs.blockIndex as number | null;
    const old = index == null ? undefined : loaded.get(index);
    if (old && index != null && index > last && !claimed.has(index)) {
      last = index;
      claimed.add(index);
      const key = nodeKey(node);
      const text = key === old.key ? old.text : nodeMarkdown(node);
      if (!text.trim()) return;
      flush();
      kept.add(index);
      after = index;
      slots.push({ pos, key });
      if (text !== old.text) edits.push({ op: "replace", index, expected: old.text, text });
      return;
    }
    const text = nodeMarkdown(node);
    if (!text.trim()) return;
    slots.push({ pos, key: nodeKey(node) });
    if (fresh && fresh.after === after) fresh.texts.push(text);
    else {
      flush();
      fresh = { after, texts: [text] };
    }
  });
  flush();
  for (const [index, old] of loaded) if (!kept.has(index)) edits.push({ op: "delete", index, expected: old.text });
  return { edits, slots };
}
