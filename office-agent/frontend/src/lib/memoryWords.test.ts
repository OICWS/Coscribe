import { describe, expect, it } from "vitest";
import type { CheckStep, RememberStep, Workflow } from "../types/workflow";
import { memoryFromText, memoryPreview, memoryText } from "./memoryWords";
import { plainDetail, plainKind } from "./plainSteps";
import { applyQuick, quickFields } from "./quickEdit";
import { describeSchedule } from "./scheduleLabels";
import { fileInputs, initialSchedule, schedulePayload } from "./scheduleForm";
import { newStep, renameValue } from "./workflowEdit";
import { ROOT, scopeAt, scopes } from "./workflowTree";

const remember: RememberStep = { id: "keep", kind: "remember", title: "Keep", name: "seen", value: "{{found.ids}}" };
const check: CheckStep = {
  id: "any",
  kind: "check",
  title: "Anything new",
  conditions: [{ left: { ref: "memory.seen" }, op: "not_empty", right: null }],
};
const workflow: Workflow = {
  version: 1,
  inputs: [{ name: "doc", label: "New file", type: "file", default: null }],
  memory: [{ name: "seen", label: "Already handled", type: "list", initial: [] }],
  steps: [check, remember],
};

describe("what a task remembers, as a person reads and edits it", () => {
  it("edits a list one item per line, keeping objects", () => {
    expect(memoryText(["a", { id: 2 }], "list")).toBe('a\n{"id":2}');
    expect(memoryFromText(' a \n\n{"id":2}\n', "list")).toEqual(["a", { id: 2 }]);
    expect(memoryFromText("  ", "list")).toBeNull();
    expect(memoryFromText("12", "number")).toBe(12);
    expect(memoryPreview(["a", "b", "c", "d"])).toBe("4 items: a, b, c, …");
    expect(memoryPreview(null)).toBe("Nothing yet");
  });

  it("says what a remember step and a quiet check do", () => {
    expect(plainKind(remember)).toBe("Memory");
    expect(plainDetail(remember, workflow.inputs)).toBe("Keeps “seen” for the next run");
    expect(plainDetail({ ...check, otherwise: "end" }, [])).toBe("Ends the run quietly if this isn’t so");
  });

  it("quick-edits a remember step's value and where a check goes", () => {
    expect(quickFields(remember, []).map((f) => f.key)).toEqual(["title", "value"]);
    expect(applyQuick(remember, "value", "{{x}}")).toMatchObject({ value: "{{x}}" });
    const otherwise = quickFields(check, []).find((f) => f.key === "otherwise");
    expect(otherwise?.value).toBe("fail");
    expect(applyQuick(check, "otherwise", "end")).toMatchObject({ otherwise: "end" });
  });

  it("offers memory and the run's time to the steps, and renames a memory value everywhere", () => {
    const names = scopeAt(scopes(workflow), ROOT, 0);
    expect(names).toEqual(expect.arrayContaining(["memory.seen", "run.started_at", "run.date"]));
    const renamed = renameValue(
      { ...workflow, memory: [{ ...workflow.memory![0], name: "done" }] },
      "memory.seen",
      "memory.done",
      null,
    );
    expect(renamed.steps[0]).toMatchObject({ conditions: [{ left: { ref: "memory.done" } }] });
    expect(renamed.steps[1]).toMatchObject({ name: "done" });
    expect(newStep("remember", workflow, ["found"])).toMatchObject({
      kind: "remember",
      name: "seen",
      value: "{{found}}",
    });
  });
});

describe("the triggers besides the clock", () => {
  it("saves every few minutes and a folder with its file input", () => {
    const form = { ...initialSchedule(null, undefined), kind: "every" as const, minutes: 15 };
    expect(schedulePayload(form, [])).toEqual({ kind: "every", at: "", watch: { minutes: 15 } });
    const folder = { ...form, kind: "folder" as const, folder: "C:\\In", pattern: "" };
    expect(schedulePayload(folder, fileInputs(workflow))).toEqual({
      kind: "folder",
      at: "",
      watch: { folder: "C:\\In", pattern: "*", input: "doc" },
    });
  });

  it("describes them", () => {
    const rule = { kind: "every" as const, at: "", weekday: null, day_of_month: null, start_date: null };
    expect(describeSchedule({ ...rule, minutes: 30 })).toBe("Every 30 minutes");
    expect(describeSchedule({ ...rule, minutes: 120 })).toBe("Every 2 hours");
    expect(describeSchedule({ ...rule, kind: "folder", folder: "C:\\Users\\me\\Invoices", pattern: "*.pdf" })).toBe(
      "When a *.pdf file arrives in Invoices",
    );
  });
});
