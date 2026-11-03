import { describe, expect, it } from "vitest";
import type { ParallelStep, StepRecord, Workflow, WorkflowStep } from "../types/workflow";
import { runArms } from "./runArms";
import { childLists, listAt, scopeAt, scopes, withList } from "./workflowTree";

function note(id: string, text: string, saveAs: string | null = null): WorkflowStep {
  return { id, kind: "tool", title: id, tool: "note", args: { text }, save_as: saveAs, irreversible: false };
}

const both: ParallelStep = {
  id: "both",
  kind: "parallel",
  title: "Both at once",
  lanes: [
    { label: "Mail", steps: [note("mail", "x", "inbox")] },
    { label: "Calendar", steps: [note("cal", "y", "events")] },
  ],
};

const workflow: Workflow = { version: 1, inputs: [], steps: [note("start", "s", "before"), both, note("end", "e")] };

describe("parallel steps (decision 0036)", () => {
  it("names each lane as a list of its own", () => {
    expect(childLists(both).map(([arm]) => arm)).toEqual(["lane:0", "lane:1"]);
    const lane = { parent: "both", arm: "lane:1" as const };
    expect(listAt(workflow, lane).map((s) => s.id)).toEqual(["cal"]);
    const changed = withList(workflow, lane, [note("cal2", "z")]);
    expect((changed.steps[1] as ParallelStep).lanes.map((l) => l.steps.map((s) => s.id))).toEqual([["mail"], ["cal2"]]);
  });

  it("lets a lane read only what came before, and the steps after read every lane's results", () => {
    const at = scopes(workflow);
    expect(scopeAt(at, { parent: "both", arm: "lane:1" }, 0)).toEqual(["before"]);
    expect(scopeAt(at, { parent: null, arm: null }, 2)).toEqual(["before", "inbox", "events"]);
  });

  it("shows every lane in a run once the step started", () => {
    const record = { step_id: "both", status: "running", iteration: [] } as unknown as StepRecord;
    expect(runArms(both, record)?.taken).toEqual(["lane:0", "lane:1"]);
    expect(runArms(both, undefined)?.taken).toEqual([]);
    expect(runArms(both, undefined)?.idle).toBe("not started");
  });
});
