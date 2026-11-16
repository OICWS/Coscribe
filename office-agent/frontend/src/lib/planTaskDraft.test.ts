import { describe, expect, it } from "vitest";
import { approvedList, draftEdits, forgetPlanTaskDraft, setPlanTaskDraft, stepsOf } from "./planTaskDraft";

const base = [
  { id: "1", content: "Read", status: "completed" as const },
  { id: "2", content: "Write", status: "pending" as const },
  { id: "3", content: "Send", status: "pending" as const },
];

describe("draftEdits", () => {
  it("is undefined until the list differs from the model's", () => {
    expect(draftEdits("p1")).toBeUndefined();
    setPlanTaskDraft("p1", base, stepsOf(base));
    expect(draftEdits("p1")).toBeUndefined();
    forgetPlanTaskDraft("p1");
  });

  it("sends the kept steps in order, trimmed, with the ids they had", () => {
    const [read, write, send] = stepsOf(base);
    setPlanTaskDraft("p2", base, [
      { ...write, content: " Write it short " },
      { key: "new", content: "Check it", included: true },
      { key: "blank", content: "  ", included: true },
      { ...send, included: false },
      read,
    ]);
    expect(draftEdits("p2")).toEqual([{ id: "2", content: "Write it short" }, { content: "Check it" }, { id: "1", content: "Read" }]);
    forgetPlanTaskDraft("p2");
    expect(draftEdits("p2")).toBeUndefined();
  });

  it("counts a reorder as an edit", () => {
    const [read, write, send] = stepsOf(base);
    setPlanTaskDraft("p3", base, [write, read, send]);
    expect(draftEdits("p3")?.map((step) => step.id)).toEqual(["2", "1", "3"]);
    forgetPlanTaskDraft("p3");
  });
});

describe("approvedList", () => {
  // The same cases as TaskToolkit.replace's tests in office-agent/tests/test_task_tools.py.
  it("keeps statuses by id and numbers a new step past every old id", () => {
    expect(approvedList(base, [{ id: "3", content: "Send it" }, { content: "Check" }, { id: "1", content: "Read" }])).toEqual([
      { id: "3", content: "Send it", status: "pending" },
      { id: "4", content: "Check", status: "pending" },
      { id: "1", content: "Read", status: "completed" },
    ]);
  });

  it("treats an id no task has as a new step", () => {
    expect(approvedList(base.slice(0, 1), [{ id: "9", content: "Made up" }])).toEqual([{ id: "2", content: "Made up", status: "pending" }]);
  });
});
