import { getSchema } from "@tiptap/core";
import { Node as PMNode } from "@tiptap/pm/model";
import { describe, expect, it } from "vitest";
import { docsExtensions } from "./docsExtensions";
import { blocksToDoc, docImageUrl, docToBlocks, type Block } from "./docsEditor";

const schema = getSchema(docsExtensions);
const roundTrip = (blocks: Block[]) => docToBlocks(PMNode.fromJSON(schema, blocksToDoc(blocks)));

const DOCUMENT: Block[] = [
  { id: "b0", kind: "title", runs: [{ t: "Service agreement" }] },
  { id: "b1", kind: "heading", level: 2, runs: [{ t: "Price" }] },
  { id: "b2", kind: "paragraph", runs: [{ t: "The total is " }, { t: "100 dollars", b: true }, { t: ", see " }, { t: "schedule A", i: true, u: true }] },
  { id: "b3", kind: "locked", what: "comment", text: "A commented line" },
  { id: "b4", kind: "bullet", level: 1, runs: [{ t: "first" }] },
  { id: "b5", kind: "bullet", level: 2, runs: [{ t: "nested" }] },
  { id: "b6", kind: "bullet", level: 1, runs: [{ t: "second" }] },
  { id: "b7", kind: "number", level: 1, runs: [{ t: "step one" }] },
  { id: "b8", kind: "quote", runs: [{ t: "A quoted line" }] },
  { id: "b9", kind: "paragraph", runs: [{ t: "see " }, { t: "the site", link: "https://example.com/a" }, { t: "\nnext line" }] },
  {
    id: "b10",
    kind: "table",
    header: true,
    rows: [
      [[{ t: "item" }], [{ t: "cost" }]],
      [[{ t: "a" }], [{ t: "1", b: true }]],
    ],
  },
  { id: "b11", kind: "paragraph", runs: [] },
];

describe("blocks and the editor's document", () => {
  it("come back as they were, ids and marks included", () => {
    const { blocks } = roundTrip(DOCUMENT);
    // A locked block carries only its id back: the server keeps what it holds.
    const expected = DOCUMENT.map((b) => (b.kind === "locked" ? { id: b.id, kind: "locked" } : b));
    expect(blocks).toEqual(expected);
  });

  it("nests the list items by level and starts a new list when the kind changes", () => {
    const doc = blocksToDoc(DOCUMENT);
    const types = doc.content?.map((n) => n.type);
    expect(types).toEqual(["title", "heading", "paragraph", "lockedBlock", "bulletList", "orderedList", "blockquote", "paragraph", "table", "paragraph"]);
    const bullets = doc.content?.[4];
    expect(bullets?.content).toHaveLength(2);
    expect(bullets?.content?.[0].content?.[1].type).toBe("bulletList");
  });

  it("shows the pictures of a locked block from where the document serves them, and sends only its id back", () => {
    const picture: Block = { id: "b7", kind: "locked", what: "image or drawing", text: "", images: ["rId4"] };
    const doc = blocksToDoc([picture], docImageUrl("t1", "a b.docx", "v9"));
    expect(doc.content?.[0].attrs?.images).toEqual(["/api/threads/t1/docs/image?path=a%20b.docx&rid=rId4&v=v9"]);
    expect(roundTrip([picture]).blocks[0]).toEqual({ id: "b7", kind: "locked" });
  });

  it("sends a picture the person added as its data once, and only the id after the file holds it", () => {
    const added: Block = { kind: "locked", what: "image or drawing", text: "" };
    const pending = blocksToDoc([added]);
    (pending.content?.[0].attrs as Record<string, unknown>).upload = "data:image/png;base64,AAAA";
    expect(docToBlocks(PMNode.fromJSON(schema, pending)).blocks[0]).toEqual({ kind: "image", data: "data:image/png;base64,AAAA" });
    expect(roundTrip([{ ...added, id: "b3" }]).blocks[0]).toEqual({ id: "b3", kind: "locked" });
  });

  it("carries a picture's width and description to the editor and back, with only the id otherwise", () => {
    const picture: Block = { id: "b4", kind: "locked", what: "image or drawing", text: "", images: ["rId4"], picture: { width: 50, alt: "A box" } };
    const doc = blocksToDoc([picture]);
    expect(doc.content?.[0].attrs?.picture).toEqual({ width: 50, alt: "A box" });
    expect(roundTrip([picture]).blocks[0]).toEqual({ id: "b4", kind: "locked", picture: { width: 50, alt: "A box" } });
  });

  it("keeps a divider and a page break as blocks of their own, with their ids", () => {
    const blocks: Block[] = [{ id: "b1", kind: "divider" }, { kind: "paragraph", runs: [{ t: "x" }] }, { id: "b3", kind: "pagebreak" }];
    expect(roundTrip(blocks).blocks).toEqual([{ id: "b1", kind: "divider" }, { id: undefined, kind: "paragraph", runs: [{ t: "x" }] }, { id: "b3", kind: "pagebreak" }]);
    expect(blocksToDoc(blocks).content?.map((n) => n.type)).toEqual(["divider", "paragraph", "pageBreak"]);
  });

  it("gives a table's first row header cells only when the file has a header row", () => {
    const table = (header: boolean): Block => ({ kind: "table", header, rows: [[[{ t: "x" }]], [[{ t: "y" }]]] });
    const first = (header: boolean) => blocksToDoc([table(header)]).content?.[0].content?.[0].content?.[0].type;
    expect(first(true)).toBe("tableHeader");
    expect(first(false)).toBe("tableCell");
    expect(roundTrip([table(false)]).blocks[0]).toMatchObject({ header: false });
  });

  it("tells where the node that carries each id sits, so a save can hand back the new ids", () => {
    const { blocks, slots } = roundTrip(DOCUMENT);
    expect(slots).toHaveLength(blocks.length);
    expect(slots[0]).toEqual({ pos: 0, type: "title" });
    const doc = PMNode.fromJSON(schema, blocksToDoc(DOCUMENT));
    blocks.forEach((block, index) => {
      if (!block.id) return;
      expect(doc.nodeAt(slots[index].pos)?.type.name).toBe(slots[index].type);
      expect(doc.nodeAt(slots[index].pos)?.attrs.blockId).toBe(block.id);
    });
  });

  it("makes a block without an id for a paragraph the person added, and keeps list levels to three", () => {
    const doc = PMNode.fromJSON(schema, {
      type: "doc",
      content: [
        { type: "paragraph", content: [{ type: "text", text: "new" }] },
        {
          type: "bulletList",
          content: [
            {
              type: "listItem",
              content: [
                { type: "paragraph", content: [{ type: "text", text: "a" }] },
                { type: "bulletList", content: [{ type: "listItem", content: [{ type: "paragraph" }, { type: "bulletList", content: [{ type: "listItem", content: [{ type: "paragraph" }, { type: "bulletList", content: [{ type: "listItem", content: [{ type: "paragraph" }] }] }] }] }] }] },
              ],
            },
          ],
        },
      ],
    });
    const { blocks } = docToBlocks(doc);
    expect(blocks[0]).toEqual({ id: undefined, kind: "paragraph", runs: [{ t: "new" }] });
    expect(blocks.map((b) => ("level" in b ? b.level : 0))).toEqual([0, 1, 2, 3, 3]);
  });
});
