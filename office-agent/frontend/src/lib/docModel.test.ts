// @vitest-environment jsdom
import { getSchema } from "@tiptap/core";
import { Node as PMNode } from "@tiptap/pm/model";
import { describe, expect, it } from "vitest";
import type { DocBlock } from "./docFile";
import { docContent, docEdits, docExtensions, loadedOf, nodeMarkdown, type Loaded } from "./docModel";

const schema = getSchema(docExtensions);
const blocks = (texts: string[], kinds: string[] = []): DocBlock[] => texts.map((text, index) => ({ index, kind: kinds[index] ?? "paragraph", text }));

function open(texts: string[], kinds: string[] = []) {
  const read = blocks(texts, kinds);
  const doc = PMNode.fromJSON(schema, docContent(read));
  return { doc, loaded: loadedOf(doc, read) };
}

type Json = { content: Json[]; [key: string]: unknown };

const edit = (doc: PMNode, change: (json: Json) => void, loaded: Map<number, Loaded>) => {
  const json = doc.toJSON() as Json;
  change(json);
  return docEdits(PMNode.fromJSON(schema, json), loaded);
};
const para = (text: string, blockIndex?: number) =>
  ({ type: "paragraph", attrs: { blockIndex: blockIndex ?? null }, content: [{ type: "text", text }] }) as unknown as Json;

describe("callouts", () => {
  it("shows a GitHub alert as a callout node and writes it back unchanged until it is edited", () => {
    const { doc, loaded } = open(["> [!WARNING]\n> Mind the gap.\n>\n> And the step."], ["callout"]);
    expect(doc.child(0).type.name).toBe("callout");
    expect(doc.child(0).attrs.type).toBe("WARNING");
    expect(doc.child(0).childCount).toBe(2);
    expect(docEdits(doc, loaded).edits).toEqual([]);
    expect(nodeMarkdown(doc.child(0))).toBe("> [!WARNING]\n> Mind the gap.\n>\n> And the step.");
  });

  it("writes a changed kind, and keeps a callout with more than paragraphs as its source", () => {
    const { doc, loaded } = open(["> [!NOTE]\n> Careful", "> [!TIP]\n> - one\n> - two"], ["callout", "callout"]);
    expect(doc.child(1).type.name).toBe("rawBlock");
    const { edits } = edit(doc, (json) => ((json.content[0].attrs as { type: string }).type = "CAUTION"), loaded);
    expect(edits).toEqual([{ op: "replace", index: 0, expected: "> [!NOTE]\n> Careful", text: "> [!CAUTION]\n> Careful" }]);
  });
});

describe("docEdits", () => {
  it("names nothing for a document nobody changed, whatever the markdown's own spelling", () => {
    const { doc, loaded } = open(["# Title", "Some **bold** words", "* star item\n* second", "| a | b |\n|-|-|\n| 1 | 2 |", "- [ ] todo\n- [x] done", "![a picture](assets/a.png)"], ["heading", "paragraph", "list", "table", "list", "paragraph"]);
    expect(docEdits(doc, loaded).edits).toEqual([]);
  });

  it("keeps the text of a block it cannot show", () => {
    const { doc, loaded } = open(["<div class=\"x\">\nraw\n</div>", "```chart\nbar\n| a | b |\n| --- | --- |\n| x | 1 |\n```"], ["html", "chart"]);
    expect(doc.child(0).type.name).toBe("rawBlock");
    expect(nodeMarkdown(doc.child(1))).toContain("| x | 1 |");
    expect(docEdits(doc, loaded).edits).toEqual([]);
  });

  it("replaces only the block whose text changed", () => {
    const { doc, loaded } = open(["First", "Second", "Third"]);
    const { edits } = edit(doc, (json) => (json.content[1] = para("Second, changed", 1)), loaded);
    expect(edits).toEqual([{ op: "replace", index: 1, expected: "Second", text: "Second, changed" }]);
  });

  it("inserts new blocks after the one before them, made together as one insert", () => {
    const { doc, loaded } = open(["First", "Second"]);
    const { edits, slots } = edit(
      doc,
      (json) => json.content.splice(1, 0, para("New one"), { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "New two" }] } as unknown as Json),
      loaded,
    );
    expect(edits).toEqual([{ op: "insert", after: 0, text: "New one\n\n## New two" }]);
    expect(slots).toHaveLength(4);
  });

  it("inserts before the first block after -1", () => {
    const { doc, loaded } = open(["First"]);
    const { edits } = edit(doc, (json) => json.content.unshift(para("Zero")), loaded);
    expect(edits).toEqual([{ op: "insert", after: -1, text: "Zero" }]);
  });

  it("deletes a block that is gone or emptied, and never inserts after it", () => {
    const { doc, loaded } = open(["First", "Second", "Third"]);
    const { edits } = edit(
      doc,
      (json) => {
        json.content[1] = { type: "paragraph" } as unknown as Json;
        json.content.splice(2, 0, para("Added"));
        json.content.splice(0, 1);
      },
      loaded,
    );
    expect(edits).toContainEqual({ op: "delete", index: 0, expected: "First" });
    expect(edits).toContainEqual({ op: "delete", index: 1, expected: "Second" });
    expect(edits).toContainEqual({ op: "insert", after: -1, text: "Added" });
  });

  it("takes a block that moved as a new block and deletes its old place", () => {
    const { doc, loaded } = open(["A", "B", "C"]);
    const { edits } = edit(doc, (json) => json.content.push(json.content.shift() as Json), loaded);
    expect(edits).toEqual([
      { op: "insert", after: 2, text: "A" },
      { op: "delete", index: 0, expected: "A" },
    ]);
  });

  it("writes a block pasted twice once as itself and once as a new block", () => {
    const { doc, loaded } = open(["A", "B"]);
    const { edits } = edit(doc, (json) => json.content.splice(1, 0, structuredClone(json.content[0])), loaded);
    expect(edits).toEqual([{ op: "insert", after: 0, text: "A" }]);
  });

  it("writes what the person typed as markdown", () => {
    const { doc, loaded } = open(["Plain"]);
    const typed = {
      type: "paragraph",
      attrs: { blockIndex: 0 },
      content: [
        { type: "text", text: "Plain " },
        { type: "text", text: "bold", marks: [{ type: "bold" }] },
        { type: "text", text: " " },
        { type: "text", text: "site", marks: [{ type: "link", attrs: { href: "https://a.b" } }] },
      ],
    } as unknown as Json;
    const { edits } = edit(doc, (json) => (json.content[0] = typed), loaded);
    expect(edits).toEqual([{ op: "replace", index: 0, expected: "Plain", text: "Plain **bold** [site](https://a.b)" }]);
  });
});
