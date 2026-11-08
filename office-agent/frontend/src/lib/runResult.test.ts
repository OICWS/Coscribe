import { describe, expect, it } from "vitest";
import type { ScheduledRun } from "../types/settings";
import type { StepRecord, Workflow } from "../types/workflow";
import { fileParts, plainError, runAt, runNotes, runResultText } from "./runResult";

const workflow = {
  version: 1,
  inputs: [],
  steps: [
    { kind: "llm", id: "draft", title: "Draft", prompt: "", fields: [] },
    { kind: "tool", id: "read", title: "Read", tool: "read_file", args: {} },
    { kind: "llm", id: "brief", title: "Brief", prompt: "", fields: [] },
  ],
} as unknown as Workflow;

const LONG = "Revenue was 12,840 from 87 orders, and four tickets are urgent today.";

function record(step_id: string, status: StepRecord["status"], finished: string, extra: Partial<StepRecord> = {}) {
  return {
    step_id,
    status,
    started_at: null,
    finished_at: finished,
    output: null,
    error: null,
    checks: null,
    note: null,
    iteration: [],
    permission: null,
    agent: null,
    ...extra,
  } as StepRecord;
}

const run = (status: ScheduledRun["status"], steps: StepRecord[]) => ({ status, steps }) as unknown as ScheduledRun;

describe("runResultText", () => {
  it("takes the longest text of the last finished AI step, not a tool's output", () => {
    const steps = [
      record("draft", "done", "07:30:01", { output: { text: `${LONG} An earlier draft.` } }),
      record("brief", "done", "07:30:09", { output: { count: 4, text: LONG, title: "Morning" } }),
      record("read", "done", "07:30:10", { output: `${LONG} ${LONG}` }),
    ];
    expect(runResultText(workflow, run("completed", steps))).toEqual({ stepId: "brief", text: LONG });
  });

  it("goes back to an earlier AI step when the last one wrote only short values", () => {
    const steps = [
      record("draft", "done", "07:30:01", { output: LONG }),
      record("brief", "done", "07:30:09", { output: { count: 4, name: "Hartmann" } }),
    ];
    expect(runResultText(workflow, run("failed", steps))?.stepId).toBe("draft");
    expect(runResultText(workflow, run("failed", [steps[1]]))).toBeNull();
  });
});

describe("runAt", () => {
  it("is the failure that came first, not the block it failed", () => {
    const steps = [
      record("gather", "failed", "07:30:52"),
      record("tickets", "failed", "07:30:01"),
      record("chat", "failed", "07:30:00", { recovered: "skipped" }),
    ];
    expect(runAt(run("failed", steps))?.step_id).toBe("tickets");
  });

  it("is the last step waiting on a run that waits for the person", () => {
    const steps = [record("gather", "running", ""), record("ok", "waiting", "")];
    expect(runAt(run("needs_approval", steps))?.step_id).toBe("ok");
    expect(runAt(run("completed", steps))).toBeUndefined();
  });
});

describe("runNotes", () => {
  it("says each recovered or retried step once", () => {
    const steps = [
      record("read", "failed", "1", { recovered: "item_skipped", iteration: [0] }),
      record("read", "failed", "2", { recovered: "item_skipped", iteration: [1] }),
      record("brief", "done", "3", { attempts: 2 }),
    ];
    expect(runNotes(run("completed", steps), (id) => id)).toEqual([
      "“read” failed on an item, which was skipped",
      "Tried “brief” again once before it worked",
    ]);
  });
});

describe("plainError", () => {
  it("says common failures plainly and keeps the first line of the rest", () => {
    expect(plainError("[Errno 2] No such file or directory: 'C:\\Reports\\may.xlsx'")).toBe(
      "There is no file may.xlsx",
    );
    expect(plainError("page.goto: net::ERR_NAME_NOT_RESOLVED at https://x.example")).toBe(
      "The page couldn't be reached",
    );
    expect(plainError("Not allowed: writing outside the folder")).toBe("You said no to a step, so it stopped there");
    expect(plainError("\nThe model didn't return the required fields: total\nTraceback")).toBe(
      "The model didn't return the required fields: total",
    );
    expect(plainError(null)).toBeNull();
  });
});

describe("fileParts", () => {
  it("splits either kind of slash", () => {
    expect(fileParts("Briefings/2026-11-02.md")).toEqual({ name: "2026-11-02.md", folder: "Briefings" });
    expect(fileParts("C:\\Work\\out.xlsx")).toEqual({ name: "out.xlsx", folder: "C:\\Work" });
  });
});
