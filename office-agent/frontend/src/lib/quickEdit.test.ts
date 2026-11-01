import { describe, expect, it } from "vitest";
import type { Workflow, WorkflowInput, WorkflowStep } from "../types/workflow";
import { applyQuick, quickFields, replaceStep } from "./quickEdit";

const inputs: WorkflowInput[] = [{ name: "dept", label: "Department", type: "choice", default: null, options: ["A"] }];
const read: WorkflowStep = {
  id: "read",
  kind: "tool",
  title: "Read",
  tool: "read_file",
  args: { path: "reports/{{dept}}/sales.csv", sheet: "Sheet1", limit: 50 },
  save_as: "rows",
  irreversible: false,
};

describe("the simple view's quick edit", () => {
  it("offers a step's fixed values and only shows what comes from elsewhere", () => {
    const fields = quickFields(read, inputs);
    expect(fields.map((f) => [f.key, f.kind])).toEqual([
      ["title", "text"],
      ["arg:path", "shown"],
      ["arg:sheet", "text"],
      ["arg:limit", "number"],
      ["irreversible", "lock"],
    ]);
    expect(fields[1].value).toBe("reports/[Department]/sales.csv");
  });

  it("marks a step that can't be undone but never unmarks it", () => {
    const marked = applyQuick(read, "irreversible", true);
    expect(marked).toMatchObject({ irreversible: true });
    expect(applyQuick(marked, "irreversible", false)).toMatchObject({ irreversible: true });
  });

  it("changes a condition's value and a path's value in place", () => {
    const branch: WorkflowStep = {
      id: "b",
      kind: "branch",
      title: "Big?",
      conditions: [
        { left: { ref: "total" }, op: "gt", right: { value: 100 } },
        { left: { ref: "count" }, op: "gt", right: { ref: "limit" } },
      ],
      match: "any",
      then: [],
      otherwise: [],
    };
    const fields = quickFields(branch, inputs);
    expect(fields.map((f) => f.label)).toEqual(["Name", "If the total is more than", "Condition"]);
    expect(fields[2]).toMatchObject({ kind: "shown", value: "Or if the count is more than the limit" });
    const changed = applyQuick(branch, "cond:0", 250);
    expect(changed.kind === "branch" && changed.conditions[0].right).toEqual({ value: 250 });

    const choice: WorkflowStep = {
      id: "c",
      kind: "choice",
      title: "By dept",
      value: "dept",
      cases: [{ is: "A", steps: [] }],
      otherwise: [],
    };
    expect(quickFields(choice, inputs)[1].label).toBe("Path 1, when “Department” is");
    expect(applyQuick(choice, "case:0", "B")).toMatchObject({ cases: [{ is: "B", steps: [] }] });
  });

  it("replaces a step wherever it sits", () => {
    const workflow: Workflow = {
      version: 1,
      inputs,
      steps: [
        {
          id: "c",
          kind: "choice",
          title: "By dept",
          value: "dept",
          cases: [{ is: "A", steps: [read] }],
          otherwise: [],
        },
      ],
    };
    const next = replaceStep(workflow, "read", { ...read, title: "Read it" });
    const step = next.steps[0];
    expect(step.kind === "choice" && step.cases[0].steps[0].title).toBe("Read it");
  });
});
