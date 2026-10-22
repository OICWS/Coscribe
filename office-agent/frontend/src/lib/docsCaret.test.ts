import { getSchema } from "@tiptap/core";
import { Node as PMNode } from "@tiptap/pm/model";
import { describe, expect, it } from "vitest";
import { caretIn, caretOf } from "./docsCaret";
import { blocksToDoc, type Block } from "./docsEditor";
import { docsExtensions } from "./docsExtensions";

const schema = getSchema(docsExtensions);
const docOf = (texts: string[]) => PMNode.fromJSON(schema, blocksToDoc(texts.map((t): Block => ({ kind: "paragraph", runs: [{ t }] }))));
const at = (doc: PMNode, text: string, offset: number) => {
  let found = -1;
  doc.descendants((node, pos) => {
    if (node.isTextblock && node.textContent === text) found = pos + 1 + offset;
  });
  return found;
};

describe("the caret across a rebuilt document", () => {
  it("stays in its words when paragraphs are added before it", () => {
    const before = docOf(["one", "two", "three"]);
    const caret = caretOf(before, at(before, "three", 2));
    const after = docOf(["intro", "one", "two", "three"]);
    expect(caret && caretIn(after, caret)).toBe(at(after, "three", 2));
  });

  it("goes to the paragraph that took its place when its words changed", () => {
    const before = docOf(["one", "two", "three"]);
    const caret = caretOf(before, at(before, "two", 1));
    const after = docOf(["one", "two, changed by coscribe", "three"]);
    expect(caret && caretIn(after, caret)).toBe(at(after, "two, changed by coscribe", 1));
  });

  it("stops at the end of a shorter paragraph, and has nowhere to go in an empty document", () => {
    const before = docOf(["a long paragraph"]);
    const caret = caretOf(before, at(before, "a long paragraph", 12));
    expect(caret && caretIn(docOf(["short"]), caret)).toBe(at(docOf(["short"]), "short", 5));
    expect(caret && caretIn(PMNode.fromJSON(schema, { type: "doc", content: [] }), caret)).toBeNull();
  });
});
