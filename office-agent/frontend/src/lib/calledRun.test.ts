import { describe, expect, it } from "vitest";
import type { ScheduledRun } from "../types/settings";
import type { Workflow } from "../types/workflow";
import { runStepTitle } from "./calledRun";

const workflow = {
  steps: [{ id: "rates", kind: "tool", title: "Read the rates", tool: "read_file", args: {} }],
} as unknown as Workflow;

const run = {
  steps: [
    {
      step_id: "rates",
      status: "failed",
      recovered: "added",
      agent: { added: { why: "", steps: [{ id: "note", kind: "tool", title: "Leave a note" }] } },
    },
  ],
} as unknown as ScheduledRun;

describe("runStepTitle", () => {
  it("names a step the run added, and the approval in front of it, by the plan's title", () => {
    expect(runStepTitle(workflow, run, "rates/added/note")).toBe("Leave a note (added by the run)");
    expect(runStepTitle(workflow, run, "rates/added/before_note")).toBe("Before “Leave a note” (added by the run)");
  });

  it("keeps the saved step's own title", () => {
    expect(runStepTitle(workflow, run, "rates")).toBe("Read the rates");
  });
});
