import { describe, expect, it } from "vitest";
import type { WorkflowInput } from "../types/workflow";
import { plainDefault, resolveDate, startingValue } from "./inputKinds";

// The same days as workflow_spec/inputs.py works out (tests/test_workflow_paths.py).
describe("an input's relative date", () => {
  it("is worked out on the day the run starts", () => {
    const wednesday = new Date(2026, 2, 4);
    expect(resolveDate("last_month_start", wednesday)).toBe("2026-02-01");
    expect(resolveDate("last_month_end", wednesday)).toBe("2026-02-28");
    expect(resolveDate("week_start", wednesday)).toBe("2026-03-02");
    expect(resolveDate("last_week_end", wednesday)).toBe("2026-03-01");
    expect(resolveDate("last_month_start", new Date(2026, 0, 15))).toBe("2025-12-01");
  });

  it("reads in words and starts a run with the day it stands for", () => {
    const month: WorkflowInput = { name: "m", label: "Month", type: "date", default: "last_month_start" };
    expect(plainDefault(month)).toBe("First day of last month");
    expect(startingValue(month, new Date(2026, 2, 4))).toBe("2026-02-01");
    const send: WorkflowInput = { name: "s", label: "Send", type: "yes_no", default: false };
    expect([plainDefault(send), startingValue(send)]).toEqual(["No", "no"]);
  });
});
