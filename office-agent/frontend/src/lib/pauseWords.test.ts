import { describe, expect, it } from "vitest";
import type { AskStep, WaitStep, WorkflowInput } from "../types/workflow";
import {
  answeredWords,
  applyAskQuick,
  applyWaitQuick,
  askQuickFields,
  askTimeoutWords,
  untilWords,
  waitQuickFields,
  waitedWords,
} from "./pauseWords";
import { plainDetail, plainKind } from "./plainSteps";

const inputs: WorkflowInput[] = [{ name: "month", label: "Month", type: "text", default: null }];

const ask = (over: Partial<AskStep> = {}): AskStep => ({
  id: "ask",
  kind: "ask",
  title: "Ask",
  message: "How much?",
  save_as: "got",
  fields: [
    { name: "amount", label: "Amount", type: "number", default: 5 },
    { name: "note", label: "Note", type: "text", required: false },
  ],
  ...over,
});

const wait = (over: Partial<WaitStep>): WaitStep => ({ id: "w", kind: "wait", title: "Wait", until: "duration", ...over });

describe("an ask step in words", () => {
  it("says what it asks for and what happens when no one answers", () => {
    expect(plainKind(ask())).toBe("Your answer");
    expect(plainDetail(ask(), inputs)).toBe("Asks you for “Amount” and “Note”");
    expect(askTimeoutWords(ask())).toBe("waits until you answer");
    const timed = ask({ timeout_hours: 24, on_timeout: "defaults" });
    expect(askTimeoutWords(timed)).toBe("after 1 day, goes on with the defaults");
    expect(plainDetail(timed, inputs)).toContain("if no one answers in 1 day, goes on with the defaults");
  });

  it("offers going on with the defaults only when every value has one", () => {
    const timed = ask({ timeout_hours: 4 });
    const then = askQuickFields(timed, inputs).find((f) => f.key === "on_timeout");
    expect(then?.options?.map((o) => o.value)).toEqual(["fail", "defaults"]);
    const missing = ask({ timeout_hours: 4, fields: [{ name: "amount", label: "Amount", type: "number" }] });
    const only = askQuickFields(missing, inputs).find((f) => f.key === "on_timeout");
    expect(only?.options?.map((o) => o.value)).toEqual(["fail"]);
    expect(only?.hint).toBeTruthy();
  });

  it("drops what happens after the timeout when it waits until answered", () => {
    const timed = ask({ timeout_hours: 4, on_timeout: "defaults" });
    expect(applyAskQuick(timed, "timeout_hours", 0)).toMatchObject({ timeout_hours: null, on_timeout: "fail" });
    expect(applyAskQuick(timed, "field:0:label", "Total")?.fields[0].label).toBe("Total");
  });

  it("shows a finished ask by its first answers", () => {
    expect(answeredWords(ask(), { amount: 12, note: "" }, null)).toBe("Answered · Amount: 12 · Note: blank");
  });
});

describe("a wait step in words", () => {
  it("says how long, until when, or for which file", () => {
    expect(plainKind(wait({ minutes: 90 }))).toBe("Wait");
    expect(plainDetail(wait({ minutes: 90 }), inputs)).toBe("Waits 1 hour 30 minutes");
    expect(plainDetail(wait({ until: "time", at: "17:00", on: "today" }), inputs)).toBe("Waits until 17:00 on today");
    expect(plainDetail(wait({ until: "file", path: "bank.csv", max_minutes: 120 }), inputs)).toBe(
      "Waits up to 2 hours for “bank.csv” to appear",
    );
  });

  it("edits a file wait in hours and shows a path with references in words", () => {
    const file = wait({ until: "file", path: "bank/{{month}}.csv", max_minutes: 1440 });
    const fields = waitQuickFields(file, inputs);
    expect(fields.find((f) => f.key === "path")).toMatchObject({ kind: "shown", value: "bank/[Month].csv" });
    expect(fields.find((f) => f.key === "max_hours")?.value).toBe(24);
    expect(applyWaitQuick(file, "max_hours", 2).max_minutes).toBe(120);
    expect(applyWaitQuick(file, "max_hours", 1000).max_minutes).toBe(10080);
  });

  it("shows a finished wait and when a pause ends", () => {
    expect(waitedWords(wait({ until: "file", path: "x" }), { found: true })).toBe("The file came");
    expect(waitedWords(wait({ until: "file", path: "x" }), { found: false })).toContain("went on without it");
    const now = new Date(2026, 10, 2, 9, 0);
    expect(untilWords(new Date(2026, 10, 2, 17, 0).toISOString(), now)).toBe("today at 17:00");
    expect(untilWords(new Date(2026, 10, 3, 9, 0).toISOString(), now)).toBe("tomorrow at 09:00");
  });
});
