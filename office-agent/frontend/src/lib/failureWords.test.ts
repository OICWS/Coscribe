import { describe, expect, it } from "vitest";
import type { ToolStep } from "../types/workflow";
import { failureFields, failureLine, withFailure } from "./failureWords";
import { applyQuick } from "./quickEdit";

const send: ToolStep = {
  id: "send",
  kind: "tool",
  title: "Send",
  tool: "send_email",
  args: {},
  save_as: null,
  irreversible: false,
};

describe("what a step does when it fails", () => {
  it("says it in one line on the step's card, and nothing when a failure just stops the run", () => {
    expect(failureLine(send)).toBeNull();
    expect(failureLine(withFailure(send, { retries: 3 }))).toBe("If it fails: 3 more tries");
    expect(failureLine(withFailure(send, { retries: 1, then: "skip" }))).toBe("If it fails: 1 more try, then skip it");
    expect(failureLine(withFailure(send, { then: "steps", steps: [send] }))).toBe("If it fails: run 1 other step");
  });

  it("stores a setting that only stops the run as none", () => {
    const tried = withFailure(send, { retries: 2, wait_seconds: 60 });
    expect(tried.on_failure).toEqual({ retries: 2, wait_seconds: 60, then: "stop", steps: [] });
    expect(withFailure(tried, { retries: 0 }).on_failure).toBeNull();
  });

  it("offers the wait only with retries, and never retries a step that can't be undone", () => {
    expect(failureFields(send).map((f) => f.key)).toEqual(["failure:retries", "failure:then"]);
    const tried = withFailure(send, { retries: 2 });
    expect(failureFields(tried).map((f) => f.key)).toEqual(["failure:retries", "failure:wait_seconds", "failure:then"]);
    const marked = applyQuick(tried, "irreversible", true) as ToolStep;
    expect(marked.on_failure).toBeNull();
    expect(failureFields(marked)[0].kind).toBe("shown");
  });

  it("shows the steps in a step's place in the quick edit and leaves changing them to the full editor", () => {
    const replaced = withFailure(send, { then: "steps", steps: [send] });
    const then = failureFields(replaced).find((f) => f.key === "failure:then");
    expect(then?.kind).toBe("shown");
    expect(then?.value).toBe("Run 1 other step in its place. Change them in the full editor.");
  });
});
