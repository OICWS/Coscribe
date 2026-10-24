import { describe, expect, it } from "vitest";
import type { LogItem } from "../state/reducer";
import { groupToolRuns, groupTurns } from "./transcriptGrouping";
import { foldTaskCard, planPanelData, taskListOf, type TaskCardEntry } from "./taskCard";

type Of<K extends LogItem["kind"]> = Extract<LogItem, { kind: K }>;

let seq = 0;
const id = () => `i${++seq}`;
const agent = (text = "narration"): Of<"agent"> => ({ id: id(), kind: "agent", text, streaming: false });
const tool = (toolName: string, args: Record<string, unknown> = {}, result?: unknown, isError?: boolean): Of<"tool"> => ({
  id: id(),
  kind: "tool",
  toolName,
  arguments: args,
  ...(result !== undefined && { result }),
  ...(isError && { isError }),
});
const create = (taskId: string, content: string) => tool("task_create", { content }, { id: taskId, content, status: "pending" });
const update = (taskId: string, content: string, status: string) =>
  tool("task_update", { task_id: taskId, status }, { id: taskId, content, status });
const approval = (status: Of<"approval">["status"]): Of<"approval"> => ({ id: id(), kind: "approval", toolName: "write_file", arguments: {}, status });

const fold = (items: LogItem[], live = false) => foldTaskCard(groupToolRuns(items), live);
const cardOf = (entries: ReturnType<typeof fold>) => entries.find((e): e is TaskCardEntry => e.kind === "task_card");

describe("taskListOf", () => {
  it("replays creates and updates from their results", () => {
    const items = [create("1", "Read"), create("2", "Write"), update("1", "Read", "completed")];
    expect(taskListOf(items)).toEqual([
      { id: "1", content: "Read", status: "completed" },
      { id: "2", content: "Write", status: "pending" },
    ]);
  });

  it("moves as soon as a call is made, before its result is back", () => {
    const items = [create("1", "Read"), tool("task_update", { task_id: "1", status: "in_progress" })];
    expect(taskListOf(items)[0].status).toBe("in_progress");
    expect(taskListOf([tool("task_create", { content: "Draft" })])).toEqual([
      expect.objectContaining({ content: "Draft", status: "pending" }),
    ]);
  });

  it("takes a listed set of tasks as the whole list", () => {
    const listed = [{ id: "7", content: "Only", status: "in_progress" }];
    expect(taskListOf([create("1", "Old"), tool("task_list", {}, listed)])).toEqual(listed);
  });

  it("reads a result that arrives as a JSON string", () => {
    const text = JSON.stringify({ id: "3", content: "Text", status: "pending" });
    expect(taskListOf([tool("task_create", { content: "Text" }, text)])).toEqual([{ id: "3", content: "Text", status: "pending" }]);
  });
});

describe("planPanelData", () => {
  it("has the list and the plan last proposed", () => {
    const plans: LogItem[] = [
      { id: id(), kind: "plan", plan: "first", status: "revise" },
      { id: id(), kind: "plan", plan: "second", status: "pending" },
    ];
    expect(planPanelData([create("1", "A"), ...plans])).toEqual({ tasks: [{ id: "1", content: "A", status: "pending" }], plan: "second" });
    expect(planPanelData([agent()])).toEqual({ tasks: [], plan: null });
  });
});

describe("foldTaskCard", () => {
  it("leaves a turn without a task list as it is", () => {
    const entries = groupToolRuns([agent(), tool("read_file")]);
    expect(foldTaskCard(entries, false)).toBe(entries);
  });

  it("replaces the narration and the calls of the stretch with one card", () => {
    const items = [
      agent("plan it"),
      create("1", "Read"),
      create("2", "Write"),
      update("1", "Read", "in_progress"),
      tool("read_file"),
      agent("now writing"),
      update("1", "Read", "completed"),
      update("2", "Write", "in_progress"),
      tool("write_file"),
      update("2", "Write", "completed"),
      agent("All done."),
    ];
    const entries = fold(items);
    expect(entries.map((e) => e.kind)).toEqual(["agent", "task_card", "agent"]);
    const card = cardOf(entries);
    expect(card?.tasks.map((t) => t.status)).toEqual(["completed", "completed"]);
    expect(card?.calls["1"]).toHaveLength(1);
    expect(card?.calls["2"]).toHaveLength(1);
    expect(entries[2]).toMatchObject({ text: "All done." });
  });

  it("keeps calls made before the list in their own run", () => {
    const entries = fold([tool("list_files"), create("1", "A"), tool("read_file")]);
    expect(entries.map((e) => e.kind)).toEqual(["tool_run", "task_card"]);
  });

  it("puts a call made while no item is in progress under the card", () => {
    const card = cardOf(fold([create("1", "A"), tool("read_file")]));
    expect(card?.calls[""]).toHaveLength(1);
  });

  it("marks the item a failed call ran under", () => {
    const card = cardOf(
      fold([create("1", "A"), create("2", "B"), update("1", "A", "in_progress"), tool("run_python_script", {}, "boom", true), update("1", "A", "completed")]),
    );
    expect(card?.failed).toEqual(["1"]);
  });

  it("leaves an approval waiting on the person outside the card", () => {
    const entries = fold([create("1", "A"), update("1", "A", "in_progress"), tool("read_file"), approval("pending")]);
    expect(entries.map((e) => e.kind)).toEqual(["task_card", "tool_run"]);
    expect(cardOf(entries)?.calls["1"]).toHaveLength(1);
  });

  it("keeps the reply after an unfinished list once the turn is over, and hides it while live", () => {
    const items = [create("1", "A"), update("1", "A", "in_progress"), tool("read_file"), agent("so far")];
    expect(fold(items, false).map((e) => e.kind)).toEqual(["task_card", "agent"]);
    expect(fold(items, true).map((e) => e.kind)).toEqual(["task_card"]);
  });

  it("shows the reply written after a finished list while the turn is still live", () => {
    const items = [create("1", "A"), update("1", "A", "completed"), agent("summary")];
    expect(fold(items, true).map((e) => e.kind)).toEqual(["task_card", "agent"]);
  });
});

describe("a later turn that only updates the list", () => {
  it("draws the whole list, from what the turns before left", () => {
    const first = [{ id: id(), kind: "user", text: "go", turnIndex: 0 } as const, create("1", "Read"), create("2", "Write")];
    const second = [{ id: id(), kind: "user", text: "next", turnIndex: 1 } as const, update("1", "Read", "completed")];
    const turns = groupTurns([...first, ...second]);
    expect(turns.map((t) => t.tasksBefore.length)).toEqual([0, 2]);
    const card = cardOf(foldTaskCard(groupToolRuns(turns[1].items), false, turns[1].tasksBefore));
    expect(card?.tasks.map((t) => [t.content, t.status])).toEqual([
      ["Read", "completed"],
      ["Write", "pending"],
    ]);
  });

  it("draws a call under the item that started last when several run at once", () => {
    const read = tool("read_file");
    const write = tool("write_file");
    const items = [
      create("1", "A"),
      create("2", "B"),
      update("1", "A", "in_progress"),
      read,
      update("2", "B", "in_progress"),
      write,
      update("2", "B", "completed"),
    ];
    const card = cardOf(fold(items));
    expect(card?.calls["1"]).toEqual([read]);
    expect(card?.calls["2"]).toEqual([write]);
    expect(card?.tasks.map((t) => t.status)).toEqual(["in_progress", "completed"]);
  });

  it("marks an item waiting while an approval for it is pending", () => {
    const items = [create("1", "A"), create("2", "B"), update("1", "A", "in_progress"), update("2", "B", "in_progress"), approval("pending")];
    expect(cardOf(fold(items, true))?.waiting).toEqual(["2"]);
    expect(cardOf(fold([create("1", "A"), update("1", "A", "in_progress"), approval("pending"), update("1", "A", "completed")], true))?.waiting).toEqual([]);
  });

  it("marks an item waiting while a question for the person is pending", () => {
    const question: LogItem = { id: id(), kind: "question", questions: [], status: "pending" };
    const items = [create("1", "A"), update("1", "A", "in_progress"), tool("read_file"), question];
    expect(cardOf(fold(items, true))?.waiting).toEqual(["1"]);
  });

  it("binds a started background task to the item in progress, from the saved history too", () => {
    const items = [
      create("1", "A"),
      create("2", "B"),
      update("1", "A", "in_progress"),
      tool("spawn_agent_background", {}, { task_id: "agent-1", status: "running" }),
      update("2", "B", "in_progress"),
      tool("run_background_script", {}, JSON.stringify({ task_id: "script-1" })),
      tool("run_background_command", {}, { task_id: "cmd-1" }),
      tool("run_background_script", {}),
    ];
    expect(cardOf(fold(items))?.bound).toEqual({ "1": ["agent-1"], "2": ["script-1", "cmd-1"] });
  });

  it("binds nothing started while no item is in progress", () => {
    const items = [create("1", "A"), tool("run_background_script", {}, { task_id: "script-1" }), update("1", "A", "in_progress")];
    expect(cardOf(fold(items))?.bound).toEqual({});
  });
});
