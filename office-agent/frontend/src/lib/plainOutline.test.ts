import { describe, expect, it } from "vitest";
import type { Workflow, WorkflowStep } from "../types/workflow";
import { plainOutline, waitsForYou } from "./plainOutline";

const read = (id: string, path: string): WorkflowStep => ({
  id,
  kind: "tool",
  title: `Read ${id}`,
  tool: "read_file",
  args: { path },
  save_as: id,
  irreversible: false,
});

const workflow: Workflow = {
  version: 1,
  inputs: [{ name: "day", label: "Day", type: "date", default: null }],
  steps: [
    {
      id: "gather",
      kind: "parallel",
      title: "Gather",
      lanes: [
        { label: "Agenda", steps: [read("agenda", "C:\\Users\\Allen\\OneDrive\\Calendar exports\\{{day}}.ics")] },
        { label: "Mail", steps: [read("mail", "mail.txt")] },
      ],
    },
    {
      id: "write",
      kind: "llm",
      title: "Write the briefing",
      prompt: "x",
      fields: [
        { name: "headline", type: "text", description: "" },
        { name: "things_to_watch", type: "list", description: "" },
      ],
      model: null,
      save_as: "brief",
      on_failure: { retries: 2, wait_seconds: 10, then: "skip", steps: [] },
    },
    {
      id: "urgent",
      kind: "branch",
      title: "Anything urgent?",
      conditions: [{ left: { count: "brief.things_to_watch" }, op: "gt", right: { value: 0 } }],
      then: [{ id: "ok", kind: "approval", title: "Check the email", message: "" } as WorkflowStep],
      otherwise: [],
    },
  ],
};

describe("plainOutline", () => {
  const [gather, write, urgent] = plainOutline(workflow);

  it("puts each lane's steps under its name, with a short path", () => {
    expect(gather.detail).toBe("At the same time");
    expect(gather.groups.map((group) => group.label)).toEqual(["Agenda", "Mail"]);
    expect(gather.groups[0].rows[0].detail).toBe("Reads “…\\Calendar exports\\[Day].ics”");
  });

  it("says what a model step works out, and what happens when it fails only when set", () => {
    expect(write.detail).toBe("Works out headline and things to watch");
    expect(write.notes).toEqual(["If it fails: 2 more tries, then skip it"]);
    expect(urgent.notes).toEqual([]);
  });

  it("reads a branch's condition and drops an empty arm", () => {
    expect(urgent.detail).toBe("If the number of the brief’s things to watch is more than 0");
    expect(urgent.groups).toHaveLength(1);
    expect(urgent.groups[0].label).toBeNull();
  });

  it("finds the steps that wait for the person, inside blocks too", () => {
    expect(waitsForYou(workflow).map((step) => step.id)).toEqual(["ok"]);
  });
});
