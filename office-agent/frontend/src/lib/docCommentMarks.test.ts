// @vitest-environment jsdom
import { getSchema } from "@tiptap/core";
import { Node as PMNode } from "@tiptap/pm/model";
import { describe, expect, it } from "vitest";
import { quoteRange } from "./docCommentMarks";
import { docContent, docExtensions } from "./docModel";

const doc = (text: string) => PMNode.fromJSON(getSchema(docExtensions), docContent([{ index: 0, kind: "paragraph", text }]));

describe("quoteRange", () => {
  it("finds words across bold and italic runs", () => {
    const block = doc("We ship the *first* version in **May**.");
    const range = quoteRange(block.child(0), 0, "first version in May");
    expect(range && block.textBetween(range.from, range.to)).toBe("first version in May");
  });

  it("is null when the words are gone", () => {
    expect(quoteRange(doc("Plain text").child(0), 0, "missing")).toBeNull();
    expect(quoteRange(doc("Plain text").child(0), 0, "")).toBeNull();
  });
});
