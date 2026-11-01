import { describe, expect, it } from "vitest";
import type { Workflow, WorkflowStep } from "../types/workflow";
import { neededAutonomy } from "./workflowLabels";

const tool: WorkflowStep = {
  id: "a",
  kind: "tool",
  title: "Read",
  tool: "read_file",
  args: {},
  save_as: null,
  irreversible: false,
};
const agent = (autonomy: "bounded" | "high" | "full"): WorkflowStep => ({
  id: `g-${autonomy}`,
  kind: "agent",
  title: "Do it",
  autonomy,
  goal: "",
  tools: [],
  folders: [],
  sites: [],
  fields: [],
  max_steps: 10,
  model: null,
  save_as: null,
  trusted_input: false,
  irreversible: false,
});
const workflow = (steps: WorkflowStep[]): Workflow => ({
  version: 2,
  inputs: [],
  steps,
});

describe("neededAutonomy", () => {
  it("is Fixed without agent steps, and as high as the most open agent step", () => {
    expect(neededAutonomy(workflow([]))).toBe("fixed");
    expect(neededAutonomy(workflow([tool]))).toBe("fixed");
    expect(neededAutonomy(workflow([tool, agent("bounded")]))).toBe("proactive");
    expect(neededAutonomy(workflow([agent("bounded"), agent("full")]))).toBe("autonomous");
  });

  it("counts a step inside a loop", () => {
    const loop: WorkflowStep = {
      id: "l",
      kind: "loop",
      title: "Each",
      over: "rows",
      item: "row",
      steps: [agent("high")],
      collect: null,
      save_as: null,
      max_items: 10,
    };
    expect(neededAutonomy(workflow([loop]))).toBe("proactive");
  });
});
