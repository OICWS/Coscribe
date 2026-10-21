import { Extension, Node, mergeAttributes, type AnyExtension } from "@tiptap/core";
import { Blockquote } from "@tiptap/extension-blockquote";
import { ListItem } from "@tiptap/extension-list";
import { Table, TableCell, TableHeader, TableRow } from "@tiptap/extension-table";
import StarterKit from "@tiptap/starter-kit";
import { Pictures } from "./docsPictures";

/** Nodes that stand for one block of the Word file: the id the server gave it rides on them. */
const BLOCK_NODES = ["paragraph", "title", "heading", "blockquote", "listItem", "table", "lockedBlock"];

const BlockId = Extension.create({
  name: "blockId",
  addGlobalAttributes() {
    // keepOnSplit false: the paragraph made by Enter is a new block, not the old one again.
    return [{ types: BLOCK_NODES, attributes: { blockId: { default: null, rendered: false, keepOnSplit: false } } }];
  },
});

const Title = Node.create({
  name: "title",
  group: "block",
  content: "inline*",
  defining: true,
  parseHTML: () => [{ tag: "h1.docs-title" }],
  renderHTML: ({ HTMLAttributes }) => ["h1", mergeAttributes(HTMLAttributes, { class: "docs-title" }), 0],
});

const LOCKED_LABELS: Record<string, string> = {
  comment: "Comment",
  "tracked change": "Tracked change",
  field: "Contents or field",
  "image or drawing": "Picture or drawing",
  note: "Footnote",
  "page break": "Page break",
  "section break": "Section break",
  "internal link": "Link inside the document",
  table: "Table",
  "deep list": "List",
};

/** A block the editor cannot change: shown as a grey line, kept as it is, deleted only by the person. */
const LockedBlock = Node.create({
  name: "lockedBlock",
  group: "block",
  atom: true,
  selectable: true,
  draggable: false,
  addAttributes() {
    return { what: { default: "" }, text: { default: "" }, images: { default: [] as string[] }, upload: { default: "" } };
  },
  parseHTML: () => [{ tag: "div.docs-locked" }],
  renderHTML: ({ node }) => {
    const images = node.attrs.images as string[];
    return [
      "div",
      { class: images.length ? "docs-locked docs-locked-pictured" : "docs-locked", contenteditable: "false" },
      ["span", { class: "docs-locked-what" }, LOCKED_LABELS[String(node.attrs.what)] ?? "Kept as it is"],
      ...images.map((src) => ["img", { class: "docs-locked-image", src, alt: "" }] as const),
      ["span", { class: "docs-locked-text" }, String(node.attrs.text)],
    ];
  },
});

/** Exactly what the Word file can hold through the editor (decision 0019): headings 1 to 3, a title,
 * quotes, lists, tables with one paragraph per cell, bold, italic, underline and links. */
export const docsExtensions: AnyExtension[] = [
  StarterKit.configure({
    heading: { levels: [1, 2, 3] },
    blockquote: false,
    listItem: false,
    code: false,
    codeBlock: false,
    strike: false,
    horizontalRule: false,
    link: { openOnClick: false, autolink: false, protocols: ["http", "https", "mailto"] },
  }),
  Blockquote.extend({ content: "paragraph+" }),
  ListItem.extend({ content: "paragraph (bulletList | orderedList)*" }),
  BlockId,
  Title,
  LockedBlock,
  Pictures,
  Table.configure({ resizable: false }),
  TableRow,
  TableHeader.extend({ content: "paragraph" }),
  TableCell.extend({ content: "paragraph" }),
];
