import { expect, it } from "vitest";
import type { WorkflowTestProgressEvent, WorkflowStepRecord } from "../types/wire.gen";
import { testProgress } from "./workflowTest";

const event = (id: string, step: string, status: WorkflowStepRecord["status"], iteration: number[] = []): WorkflowTestProgressEvent => ({
  type: "workflow_test_progress", tool_call_id: id, step, status, done: 0, total: 4,
  record: { step_id: step, status, iteration, started_at: null, finished_at: null, output: null, error: null, checks: null, note: null, permission: null, agent: null },
});

it("keeps independent active steps and repeated loop passes, replacing each pass's status", () => {
  let state = testProgress(null, event("a", "left", "running"));
  state = testProgress(state, event("a", "right", "running"));
  state = testProgress(state, event("a", "inside", "done", [0]));
  state = testProgress(state, event("a", "inside", "running", [1]));
  state = testProgress(state, event("a", "left", "done"));
  expect(state.records?.filter(record => record.status === "running").map(record => record.step_id)).toEqual(["right", "inside"]);
  expect(state.records?.filter(record => record.step_id === "inside").map(record => record.iteration)).toEqual([[0], [1]]);
});

it("starts a new test with no records from the old test", () => {
  const previous = testProgress(null, event("a", "left", "failed"));
  const next = testProgress(previous, event("b", "right", "running"));
  expect(next.records?.map(record => record.step_id)).toEqual(["right"]);
});
