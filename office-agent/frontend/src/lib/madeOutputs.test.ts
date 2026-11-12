import { describe, expect, it } from "vitest";
import type { ActivityFile } from "../types/session";
import { changedWhen, closeKey, externalType, folderOf, madeOutputs, titleOf } from "./madeOutputs";

const file = (path: string, extra: Partial<ActivityFile> = {}): ActivityFile => ({
  path,
  name: path.split(/[\\/]/).pop() ?? path,
  exists: true,
  openable: true,
  modified_at: "2026-11-11T06:00:00Z",
  action: "created",
  ...extra,
});

describe("madeOutputs", () => {
  it("sorts the conversation's files into what opens in a panel, pictures and files of other programs", () => {
    const made = madeOutputs([file("deck.pptx"), file("chart.png"), file("sales.xlsx"), file("plan.md"), file("run.py")], new Set(["plan.md"]));
    expect(made.map((m) => m.kind)).toEqual(["artifact", "images", "external", "artifact"]);
    expect(made[0]).toMatchObject({ kind: "artifact", artifact: "slides" });
    expect(made[2]).toMatchObject({ kind: "external", type: "Excel" });
    expect(made[3]).toMatchObject({ kind: "artifact", artifact: "docs" });
  });

  it("leaves out a Markdown file the server didn't read as a Doc", () => {
    expect(madeOutputs([file("notes.md")], new Set())).toEqual([]);
  });

  it("puts every picture in one notice, where the newest one was", () => {
    const made = madeOutputs([file("a.pptx"), file("one.png"), file("b.pdf"), file("two.jpg")], new Set());
    expect(made.map((m) => m.kind)).toEqual(["artifact", "images", "external"]);
    expect(made[1]).toMatchObject({ files: [{ path: "one.png" }, { path: "two.jpg" }] });
  });

  it("counts a design's pages as the one design", () => {
    const made = madeOutputs([file("site.design/home.html"), file("site.design/about.html")], new Set());
    expect(made).toHaveLength(1);
    expect(made[0]).toMatchObject({ kind: "artifact", artifact: "design", file: { path: "site.design.json", name: "site.design.json" } });
  });

  it("leaves out a gone file and one the computer can't open", () => {
    expect(madeOutputs([file("gone.pdf", { exists: false }), file("odd.csv", { openable: false })], new Set())).toEqual([]);
  });
});

describe("notice words", () => {
  it("names a file's program, folder and title", () => {
    expect(externalType("Q3.XLSX")).toBe("Excel");
    expect(externalType("notes.txt")).toBeNull();
    expect(folderOf("reports\\2026\\q3.pdf")).toBe("reports\\2026");
    expect(folderOf("q3.pdf")).toBe("");
    expect(titleOf("site.design.json")).toBe("site");
    expect(titleOf("Board update.pptx")).toBe("Board update");
  });

  it("says when a file changed", () => {
    const now = new Date("2026-11-11T06:05:00Z");
    expect(changedWhen("2026-11-11T06:00:00Z", now)).toBe("5m ago");
    expect(changedWhen(null, now)).toBe("");
  });

  it("brings a closed notice back once its file changes", () => {
    expect(closeKey("t", file("a.pdf"))).not.toBe(closeKey("t", file("a.pdf", { modified_at: "2026-11-11T07:00:00Z" })));
  });
});
