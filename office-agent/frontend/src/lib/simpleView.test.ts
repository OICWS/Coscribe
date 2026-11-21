import { describe, expect, it } from "vitest";
import type { LogItem } from "../state/reducer";
import { foldTaskCard } from "./taskCard";
import { currentActivity, onlyPendingApprovals, simpleEntries, waitsOnThePerson } from "./simpleView";
import { groupToolRuns, groupTurns } from "./transcriptGrouping";

type Tool = Extract<LogItem, { kind: "tool" }>;

const user: LogItem = { id: "u", kind: "user", text: "tidy the sales sheet", turnIndex: 0 };
const say = (id: string, text: string): LogItem => ({ id, kind: "agent", text, streaming: false });
const call = (id: string, toolName: string, extra: Partial<Tool> = {}): LogItem => ({
  id,
  kind: "tool",
  toolName,
  arguments: { path: "sales.xlsx" },
  ...extra,
});

const items: LogItem[] = [
  user,
  say("a1", "I'll read the sheet first."),
  call("t1", "read_xlsx", { result: "ok" }),
  say("a2", "Now I'll fix the totals."),
  call("t2", "run_python_script", { result: "ok" }),
  say("a3", "Done: the totals add up now."),
];

function entriesOf(list: LogItem[], live: boolean) {
  const [turn] = groupTurns(list);
  return simpleEntries(foldTaskCard(groupToolRuns(turn.items), turn.taskPlaces), live, turn.finalAgentItem);
}

describe("simpleEntries", () => {
  it("keeps the message and the finished turn's reply, not its runs or narration", () => {
    expect(entriesOf(items, false).map((entry) => entry.id)).toEqual(["u", "a3"]);
  });

  it("shows no words while the turn runs, since the last of them may be narration", () => {
    expect(entriesOf(items, true).map((entry) => entry.id)).toEqual(["u"]);
  });

  it("keeps a run holding an approval the person has not answered", () => {
    const approval: LogItem = { id: "p1", kind: "approval", toolName: "delete_file", arguments: {}, status: "pending" };
    const kept = entriesOf([user, say("a1", "I'll delete the old copy."), approval], true);
    expect(kept.map((entry) => entry.kind)).toEqual(["user", "tool_run"]);
  });

  it("draws a waiting run as its approval alone, without the calls finished before it", () => {
    const approval: LogItem = { id: "p1", kind: "approval", toolName: "run_python_script", arguments: {}, status: "pending" };
    const [run] = entriesOf([user, call("t1", "read_file", { result: "ok" }), approval], true).filter((entry) => entry.kind === "tool_run");
    expect(run.kind === "tool_run" && onlyPendingApprovals(run).items.map((item) => item.id)).toEqual(["p1"]);
  });

  it("keeps the cards the person answers", () => {
    const question: LogItem = { id: "q1", kind: "question", questions: [], status: "answered", answers: [] };
    expect(entriesOf([user, call("t1", "read_xlsx", { result: "ok" }), question], false).map((entry) => entry.id)).toEqual(["u", "q1"]);
  });
});

describe("currentActivity", () => {
  it("names the running call's kind of work without its object", () => {
    expect(currentActivity([user, call("t1", "read_xlsx")], new Set())).toBe("Reading");
    expect(currentActivity([user, call("t1", "run_code_command")], new Set())).toBe("Running commands");
  });

  it("reads a deferred tool by its own name", () => {
    const viaUseTool = call("t1", "use_tool", { arguments: { name: "browser_click", arguments: {} } });
    expect(currentActivity([user, viaUseTool], new Set())).toBe("Browsing");
  });

  it("is Thinking between calls, and Working for a call of no listed kind", () => {
    expect(currentActivity([user, call("t1", "read_xlsx", { result: "ok" })], new Set())).toBe("Thinking");
    expect(currentActivity([user, call("t1", "save_memory")], new Set())).toBe("Working");
  });
});

describe("waitsOnThePerson", () => {
  it("is true while an approval or a question waits", () => {
    const approval: LogItem = { id: "p1", kind: "approval", toolName: "delete_file", arguments: {}, status: "pending" };
    const question: LogItem = { id: "q1", kind: "question", questions: [], status: "pending" };
    expect(waitsOnThePerson(groupTurns([user, approval])[0])).toBe(true);
    expect(waitsOnThePerson(groupTurns([user, question])[0])).toBe(true);
    expect(waitsOnThePerson(groupTurns(items)[0])).toBe(false);
  });
});
