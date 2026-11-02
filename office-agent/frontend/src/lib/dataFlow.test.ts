import { describe, expect, it } from "vitest";
import type { Workflow, WorkflowStep } from "../types/workflow";
import { dataFlow, flowRole } from "./dataFlow";

function read(id: string, path: string, saveAs: string): WorkflowStep {
  return { id, kind: "tool", title: id, tool: "read_file", args: { path }, save_as: saveAs, irreversible: false };
}

const workflow = {
  version: 1,
  inputs: [{ name: "folder", label: "Folder", type: "folder", default: null }],
  steps: [
    {
      ...read("rates", "rates.json", "rates"),
      on_failure: { retries: 0, wait_seconds: 30, then: "steps", steps: [read("old", "{{failure.step}}", "rates")] },
    },
    read("list", "{{folder}}", "files"),
    {
      id: "each",
      kind: "loop",
      title: "Each",
      over: "files",
      item: "file",
      steps: [read("one", "{{file.path}} {{rates.EUR}}", "text")],
      collect: "text",
      save_as: "texts",
      max_items: 50,
    },
  ],
  after_failure: [read("tell", "{{folder}}", "told")],
} as unknown as Workflow;

describe("a step's data on the canvas", () => {
  it("links a step to the steps that make what it reads, a value made in two places to both", () => {
    const flows = dataFlow(workflow);
    expect([...flows.get("one")!.from].sort()).toEqual(["each", "old", "rates"]);
    expect([...flows.get("rates")!.to]).toEqual(["one"]);
    expect([...flows.get("list")!.inputs]).toEqual(["folder"]);
    expect([...flows.get("tell")!.inputs]).toEqual(["folder"]);
    expect([...flows.get("list")!.to]).toEqual(["each"]);
  });

  it("names how each step relates to the one in focus", () => {
    const flows = dataFlow(workflow);
    expect(flowRole(flows, "one", "one")).toBe("focus");
    expect(flowRole(flows, "one", "rates")).toBe("feeds");
    expect(flowRole(flows, "rates", "one")).toBe("uses");
    expect(flowRole(flows, "one", "list")).toBe("other");
  });
});
