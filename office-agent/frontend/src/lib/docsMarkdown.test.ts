import { describe, expect, it } from "vitest";
import type { Block } from "./docsEditor";
import { blocksToMarkdown } from "./docsMarkdown";

const text = (t: string, marks: object = {}) => [{ t, ...marks }];

describe("blocksToMarkdown", () => {
  it("writes the title as # and headings one level down, with words marked up", () => {
    const blocks: Block[] = [
      { kind: "title", runs: text("Plan") },
      { kind: "heading", level: 1, runs: text("Goals") },
      { kind: "paragraph", runs: [{ t: "Run " }, { t: "fast", b: true }, { t: " and " }, { t: "far", i: true }, { t: ", see " }, { t: "docs", link: "https://x.test" }] },
    ];
    expect(blocksToMarkdown(blocks)).toBe("# Plan\n\n## Goals\n\nRun **fast** and *far*, see [docs](https://x.test)\n");
  });

  it("keeps a list together, nests by level and numbers every item 1", () => {
    const blocks: Block[] = [
      { kind: "bullet", level: 1, runs: text("one") },
      { kind: "bullet", level: 2, runs: text("inner") },
      { kind: "paragraph", runs: text("between") },
      { kind: "number", level: 1, runs: text("first") },
      { kind: "number", level: 1, runs: text("second") },
    ];
    expect(blocksToMarkdown(blocks)).toBe("- one\n  - inner\n\nbetween\n\n1. first\n1. second\n");
  });

  it("writes a table with its header row, a table without one with an empty header, and escapes a bar", () => {
    const rows = [[text("item"), text("a|b")], [text("x"), text("1")]];
    expect(blocksToMarkdown([{ kind: "table", header: true, rows }])).toBe("| item | a\\|b |\n| --- | --- |\n| x | 1 |\n");
    expect(blocksToMarkdown([{ kind: "table", header: false, rows }])).toBe("|   |   |\n| --- | --- |\n| item | a\\|b |\n| x | 1 |\n");
  });

  it("writes quotes and dividers, a picture as a note, and leaves out empty blocks and page breaks", () => {
    const blocks: Block[] = [
      { kind: "quote", runs: text("said") },
      { kind: "divider" },
      { kind: "locked", what: "image or drawing", text: "", images: ["rId4"] },
      { kind: "paragraph", runs: [] },
      { kind: "pagebreak" },
      { kind: "locked", what: "field", text: "Contents" },
    ];
    expect(blocksToMarkdown(blocks)).toBe("> said\n\n---\n\n[Picture]\n\nContents\n");
  });

  it("does not turn a document's own asterisks and brackets into markup", () => {
    expect(blocksToMarkdown([{ kind: "paragraph", runs: text("a*b [c] _d_") }])).toBe("a\\*b \\[c\\] \\_d\\_\n");
  });
});
