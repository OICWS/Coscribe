import { describe, expect, it } from "vitest";
import { draftPages } from "./draftPages";

const write = (path: string, extra: Record<string, unknown> = {}) => ({ toolName: "write_file", arguments: { path }, result: "ok", ...extra });
const build = { toolName: "build_pptx_from_pages", arguments: { path: "deck.pptx", pages_dir: "pages" } };

describe("draftPages", () => {
  it("shows the active deck's pages in order, even if another folder was written later", () => {
    const calls = [write("pages/10-end.svg"), write("pages/01-cover.svg"), write("icons/star.svg"), build];
    expect(draftPages(calls, "deck.pptx").map((p) => p.path)).toEqual(["pages/01-cover.svg", "pages/10-end.svg"]);
    expect(draftPages(calls, "old.pptx")).toEqual([]);
  });

  it("ends the preview once that build has finished or been denied", () => {
    const page = write("pages/01.svg");
    expect(draftPages([page], "deck.pptx")).toEqual([]);
    expect(draftPages([page, build, { ...build, result: "ok" }], "deck.pptx")).toEqual([]);
    expect(draftPages([page, { ...build, status: "denied" }], "deck.pptx")).toEqual([]);
  });

  it("counts completed writes of the same page", () => {
    const calls = [write("pages/01.svg"), write("pages/01.svg"), write("pages/02.svg", { isError: true }), build];
    expect(draftPages(calls, "deck.pptx")).toEqual([{ path: "pages/01.svg", version: 2 }]);
  });
});
