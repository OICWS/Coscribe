import { describe, expect, it } from "vitest";
import { describeArgs, describeResult, rawJson } from "./toolFields";

describe("describeArgs", () => {
  it("makes a line per argument with scalars as plain text", () => {
    expect(describeArgs({ path: "plan.md", limit: 20, force: false })).toEqual([
      { name: "path", value: "plan.md", children: [] },
      { name: "limit", value: "20", children: [] },
      { name: "force", value: "false", children: [] },
    ]);
  });

  it("indents a nested object and a list", () => {
    expect(describeArgs({ options: { mode: "fast" }, paths: ["a.md", "b.md"] })).toEqual([
      { name: "options", value: null, children: [{ name: "mode", value: "fast", children: [] }] },
      {
        name: "paths",
        value: null,
        children: [
          { name: null, value: "a.md", children: [] },
          { name: null, value: "b.md", children: [] },
        ],
      },
    ]);
  });

  it("keeps a very long value whole, for the box to wrap", () => {
    const long = "x".repeat(50_000);
    expect(describeArgs({ content: long })[0].value).toBe(long);
  });

  it("shows null as none and stops descending past the depth limit", () => {
    expect(describeArgs({ a: null })[0].value).toBe("none");
    let deep: unknown = "end";
    for (let i = 0; i < 10; i++) deep = { next: deep };
    let line = describeArgs({ deep })[0];
    let depth = 0;
    while (line.children.length > 0) {
      line = line.children[0];
      depth++;
    }
    expect(depth).toBeLessThan(10);
    expect(line.value).toContain("next");
  });

  it("has no lines for no arguments", () => {
    expect(describeArgs({})).toEqual([]);
  });
});

describe("describeResult", () => {
  it("reads a JSON string as lines", () => {
    expect(describeResult('{"merged":true,"message":"done"}')).toEqual({
      kind: "lines",
      lines: [
        { name: "merged", value: "true", children: [] },
        { name: "message", value: "done", children: [] },
      ],
    });
  });

  it("reads an object result as lines", () => {
    expect(describeResult({ exit_code: 0 })).toEqual({
      kind: "lines",
      lines: [{ name: "exit_code", value: "0", children: [] }],
    });
  });

  it("keeps text that is not JSON as it is, even when it starts like JSON", () => {
    expect(describeResult("5 files changed")).toEqual({ kind: "text", text: "5 files changed" });
    expect(describeResult("{not json")).toEqual({ kind: "text", text: "{not json" });
  });

  it("says so for an empty object", () => {
    expect(describeResult({})).toEqual({ kind: "text", text: "(empty)" });
  });
});

describe("rawJson", () => {
  it("prints a value as JSON and a string as it is", () => {
    expect(rawJson({ a: 1 })).toBe('{\n  "a": 1\n}');
    expect(rawJson("text")).toBe("text");
  });
});
