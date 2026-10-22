import { describe, expect, it } from "vitest";
import { diffLines, diffStat, withContext } from "./lineDiff";

describe("diffLines", () => {
  it("shows a first version as all added", () => {
    const rows = diffLines("", "# Plan\nstep 1");
    expect(rows.map((row) => row.kind)).toEqual(["add", "add"]);
    expect(diffStat(rows)).toEqual({ added: 2, removed: 0 });
    expect(rows[1]).toMatchObject({ oldNo: null, newNo: 2, text: "step 1" });
  });

  it("keeps the lines the two versions share and numbers them in each", () => {
    const rows = diffLines("a\nb\nc", "a\nx\nb\nc");
    expect(rows.map((row) => [row.kind, row.oldNo, row.newNo])).toEqual([
      ["same", 1, 1],
      ["add", null, 2],
      ["same", 2, 3],
      ["same", 3, 4],
    ]);
  });

  it("reports a replaced line as a deletion and an addition and marks what changed in it", () => {
    const rows = diffLines("read 8-12 notes", "read 30-50 notes");
    expect(rows.map((row) => row.kind)).toEqual(["del", "add"]);
    expect(diffStat(rows)).toEqual({ added: 1, removed: 1 });
    expect(rows[0].mark).toEqual([5, 9]);
    expect(rows[1].mark).toEqual([5, 10]);
  });

  it("finds no change in equal texts", () => {
    expect(diffStat(diffLines("a\nb", "a\nb"))).toEqual({ added: 0, removed: 0 });
  });
});

describe("withContext", () => {
  it("leaves out the unchanged stretch far from a change", () => {
    const old = Array.from({ length: 12 }, (_, n) => `line ${n}`).join("\n");
    const rows = diffLines(old, old.replace("line 10", "LINE 10"));
    const entries = withContext(rows, 2);
    expect(entries[0]).toEqual({ kind: "gap", hidden: 8 });
    expect(entries.filter((entry) => entry.kind !== "gap").map((entry) => (entry as { text: string }).text)).toEqual([
      "line 8",
      "line 9",
      "line 10",
      "LINE 10",
      "line 11",
    ]);
  });

  it("shows a single unchanged line between two changes instead of a gap", () => {
    const rows = diffLines("a\nb\nc\nd\ne\nf\ng\nh\ni", "A\nb\nc\nd\ne\nf\ng\nh\nI");
    const entries = withContext(rows, 2);
    expect(entries.some((entry) => entry.kind === "gap")).toBe(true);
    const near = withContext(diffLines("a\nb\nc\nd\ne", "A\nb\nc\nd\nE"), 1);
    expect(near.filter((entry) => entry.kind === "gap")).toEqual([]);
  });
});
