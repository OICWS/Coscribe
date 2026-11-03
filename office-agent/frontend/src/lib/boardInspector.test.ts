import { describe, expect, it } from "vitest";
import { inspectorAnswer, styleChanges, treeRows, type InspectedNode } from "./boardInspector";

const leaf = (path: string, text: string): InspectedNode => ({ path, tag: "p", kind: "Text", text, children: [] });

describe("board inspector", () => {
  it("lists the tree depth first with each row's depth", () => {
    const tree: InspectedNode = { path: "", tag: "body", kind: "Column", text: "", children: [{ ...leaf("0", ""), kind: "Row", children: [leaf("0.0", "a")] }, leaf("1", "b")] };
    expect(treeRows(tree).map(({ node, depth }) => `${depth}:${node.path}`)).toEqual(["0:", "1:0", "2:0.0", "1:1"]);
  });

  it("takes only the page's own answers", () => {
    expect(inspectorAnswer({ coscribe: "inspect-tree", tree: leaf("", "x") })).toEqual({ tree: leaf("", "x") });
    expect(inspectorAnswer({ coscribe: "inspect-element", element: null })).toEqual({ element: null });
    expect(inspectorAnswer({ coscribe: "go", file: "a.html" })).toBeNull();
    expect(inspectorAnswer("hello")).toBeNull();
  });

  it("turns the typed style into what changed: new and changed values, and removed properties", () => {
    const before: [string, string][] = [
      ["color", "red"],
      ["gap", "8px"],
    ];
    expect(styleChanges(before, "color: red;\nletter-spacing: 1px; gap:12px")).toEqual({ "letter-spacing": "1px", gap: "12px" });
    expect(styleChanges(before, "gap: 8px")).toEqual({ color: "" });
    expect(styleChanges(before, "color: red; gap: 8px;")).toEqual({});
    expect(styleChanges([], "not a declaration\n: none")).toEqual({});
  });
});
