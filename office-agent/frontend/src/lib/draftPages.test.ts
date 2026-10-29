import { describe, expect, it } from "vitest";
import { draftPages } from "./draftPages";

const write = (path: string, extra: Record<string, unknown> = {}) => ({ toolName: "write_file", arguments: { path }, result: "ok", ...extra });

describe("draftPages", () => {
  it("lists the pages of the folder written to last, in the order of their names", () => {
    const calls = [write("deck/10-end.svg"), write("deck/02-agenda.svg"), write("deck/01-cover.svg"), write("icons/star.svg"), write("deck/03-body.svg")];
    expect(draftPages(calls).map((p) => p.path)).toEqual(["deck/01-cover.svg", "deck/02-agenda.svg", "deck/03-body.svg", "deck/10-end.svg"]);
  });

  it("leaves out a write that failed or has not finished, and a call that only reads", () => {
    const calls = [write("p/01.svg"), write("p/02.svg", { isError: true }), write("p/03.svg", { result: undefined }), { toolName: "read_file", arguments: { path: "p/04.svg" }, result: "x" }];
    expect(draftPages(calls).map((p) => p.path)).toEqual(["p/01.svg"]);
  });

  it("counts the writes of a page, so one written again is fetched again", () => {
    expect(draftPages([write("p/01.svg"), write("p/01.svg")])).toEqual([{ path: "p/01.svg", version: 2 }]);
  });

  it("is empty when no page was written", () => {
    expect(draftPages([write("notes.md")])).toEqual([]);
  });
});
