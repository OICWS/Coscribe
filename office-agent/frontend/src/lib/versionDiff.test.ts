import { describe, expect, it } from "vitest";
import type { Workflow } from "../types/workflow";
import { compareVersions } from "./versionDiff";

const note = (id: string, text: string) => ({
  kind: "tool" as const,
  id,
  title: id,
  tool: "note",
  args: { text },
  save_as: null,
  irreversible: false,
});

describe("compareVersions", () => {
  it("names the steps added, changed and removed, and the inputs that changed", () => {
    const older: Workflow = {
      version: 1,
      inputs: [{ name: "month", label: "Month", type: "text", default: null }],
      steps: [note("a", "x"), note("b", "y")],
    };
    const loop = { kind: "loop" as const, id: "each", title: "each", over: "month", item: "it", collect: null };
    const newer: Workflow = {
      version: 1,
      inputs: [{ name: "month", label: "Month", type: "date", default: null }],
      steps: [note("a", "changed"), { ...loop, save_as: null, max_items: 50, steps: [note("c", "z")] }],
    };
    const diff = compareVersions(older, newer);
    expect(diff.steps).toEqual([
      { id: "a", title: "a", change: "changed" },
      { id: "each", title: "each", change: "added" },
      { id: "c", title: "c", change: "added" },
      { id: "b", title: "b", change: "removed" },
    ]);
    expect(diff.inputs).toEqual(["Month"]);
    expect(diff.otherwise).toEqual([]);
  });

  it("doesn't count a block as changed when only a step inside it did", () => {
    const branch = (text: string) => ({
      kind: "branch" as const,
      id: "if",
      title: "if",
      conditions: [],
      then: [note("in", text)],
      otherwise: [],
    });
    const diff = compareVersions(
      { version: 1, inputs: [], steps: [branch("x")] },
      { version: 1, inputs: [], steps: [branch("y")] },
    );
    expect(diff.steps).toEqual([{ id: "in", title: "in", change: "changed" }]);
  });
});
