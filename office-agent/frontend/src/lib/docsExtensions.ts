import { Extension, Mark, Node, mergeAttributes, type AnyExtension } from "@tiptap/core";
import { Blockquote } from "@tiptap/extension-blockquote";
import { ListItem } from "@tiptap/extension-list";
import { Table, TableCell, TableHeader, TableRow } from "@tiptap/extension-table";
import StarterKit from "@tiptap/starter-kit";
import { Pictures } from "./docsPictures";
import { Divider, LockedBlock } from "./docsLocked";
import { lookStyle, runStyle, type Look } from "./docsLook";

/** Nodes that stand for one block of the Word file: the id the server gave it rides on them. */
const BLOCK_NODES = ["paragraph", "title", "heading", "blockquote", "listItem", "table", "lockedBlock", "divider", "pageBreak"];

const BlockId = Extension.create({
  name: "blockId",
  addGlobalAttributes() {
    // keepOnSplit false: the paragraph made by Enter is a new block, not the old one again.
    return [{ types: BLOCK_NODES, attributes: { blockId: { default: null, rendered: false, keepOnSplit: false } } }];
  },
});

/** What the file gives a paragraph (its font, spacing, rules, shading) and a table cell (fill, borders) is drawn,
 * not edited: the new paragraph made by Enter starts from the document's ordinary look. */
const LookAttributes = Extension.create({
  name: "lookAttributes",
  addGlobalAttributes() {
    return [
      {
        types: ["paragraph", "heading", "title"],
        attributes: {
          look: { default: null, rendered: true, keepOnSplit: false, parseHTML: () => null, renderHTML: (attrs: Record<string, unknown>) => (attrs.look ? { style: lookStyle(attrs.look as Look) } : {}) },
        },
      },
      {
        types: ["tableCell", "tableHeader"],
        attributes: {
          css: { default: "", keepOnSplit: false, parseHTML: (element: HTMLElement) => element.getAttribute("style") ?? "", renderHTML: (attrs: Record<string, unknown>) => (attrs.css ? { style: String(attrs.css) } : {}) },
        },
      },
    ];
  },
});

/** A run's own colour, size and font; typing beside it carries them on, and a save writes them back. */
const RunLook = Mark.create({
  name: "runLook",
  addAttributes() {
    return { c: { default: null }, sz: { default: null }, f: { default: null } };
  },
  parseHTML: () => [{ tag: "span[data-run-look]" }],
  renderHTML: ({ mark }) => ["span", { "data-run-look": "", style: runStyle({ t: "", c: mark.attrs.c ?? undefined, sz: mark.attrs.sz ?? undefined, f: mark.attrs.f ?? undefined }) }, 0],
});

const Title = Node.create({
  name: "title",
  group: "block",
  content: "inline*",
  defining: true,
  parseHTML: () => [{ tag: "h1.docs-title" }],
  renderHTML: ({ HTMLAttributes }) => ["h1", mergeAttributes(HTMLAttributes, { class: "docs-title" }), 0],
});

const PageBreak = Node.create({
  name: "pageBreak",
  group: "block",
  atom: true,
  selectable: true,
  parseHTML: () => [{ tag: "div.docs-page-break" }],
  renderHTML: () => ["div", { class: "docs-page-break", contenteditable: "false" }, ["span", {}, "Page break"]],
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
  LookAttributes,
  RunLook,
  Title,
  LockedBlock,
  Divider,
  PageBreak,
  Pictures,
  Table.configure({ resizable: false }),
  TableRow,
  TableHeader.extend({ content: "paragraph" }),
  TableCell.extend({ content: "paragraph" }),
];
