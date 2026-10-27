// @vitest-environment jsdom
import { Editor } from "@tiptap/core";
import { describe, expect, it } from "vitest";
import type { DocBlock } from "./docFile";
import { docContent, docEdits, docExtensions, loadedOf } from "./docModel";

const blocks: DocBlock[] = [
  { index: 0, kind: "heading", text: "# Plan" },
  { index: 1, kind: "paragraph", text: "We ship the *first* version in May." },
  { index: 2, kind: "list", text: "- design\n- build" },
  { index: 3, kind: "table", text: "| who | what |\n| --- | --- |\n| Ann | docs |" },
];

function open() {
  const editor = new Editor({ extensions: docExtensions, content: docContent(blocks) });
  return { editor, loaded: loadedOf(editor.state.doc, blocks) };
}

describe("the editor over a Doc", () => {
  it("names nothing before anything is typed", () => {
    const { editor, loaded } = open();
    expect(docEdits(editor.state.doc, loaded).edits).toEqual([]);
  });

  it("writes typing inside one block as that block's replace", () => {
    const { editor, loaded } = open();
    editor.commands.setTextSelection(editor.state.doc.child(0).nodeSize + 3);
    editor.commands.insertContent("XX");
    const { edits } = docEdits(editor.state.doc, loaded);
    expect(edits).toHaveLength(1);
    expect(edits[0]).toMatchObject({ op: "replace", index: 1, expected: blocks[1].text });
  });

  it("writes Enter in a paragraph as a replace and an insert, not a rewrite of the rest", () => {
    const { editor, loaded } = open();
    const start = editor.state.doc.child(0).nodeSize + 1;
    editor.commands.setTextSelection(start + 3);
    editor.commands.splitBlock();
    const { edits } = docEdits(editor.state.doc, loaded);
    expect(edits.map((e) => e.op)).toEqual(["replace", "insert"]);
  });

  it("writes a new checklist and a bold word as markdown", () => {
    const { editor, loaded } = open();
    editor.commands.setTextSelection(editor.state.doc.content.size);
    editor.chain().focus("end").insertContentAt(editor.state.doc.content.size, { type: "taskList", content: [{ type: "taskItem", attrs: { checked: true }, content: [{ type: "paragraph", content: [{ type: "text", text: "ship it" }] }] }] }).run();
    const { edits } = docEdits(editor.state.doc, loaded);
    expect(edits).toContainEqual({ op: "insert", after: 3, text: "- [x] ship it" });
  });
});
