import { describe, expect, it } from "vitest";
import type { LogItem } from "../state/reducer";
import { groupToolRuns, groupTurns } from "./transcriptGrouping";
import { foldTaskCard, planPanelData, taskCardPlaces, taskListOf, type TaskCardEntry } from "./taskCard";

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

const fold = (items: LogItem[]) => foldTaskCard(groupToolRuns(items), taskCardPlaces(items));
const cardsOf = (entries: ReturnType<typeof fold>) => entries.filter((e): e is TaskCardEntry => e.kind === "task_card");

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
    expect(foldTaskCard(entries, {})).toEqual(entries);
  });

  it("shows one card, under the last call that changed the list, and the calls and narration as they are", () => {
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
    ];
    const entries = fold(items);
    expect(entries.map((e) => e.kind)).toEqual(["agent", "tool_run", "agent", "task_card", "tool_run"]);
    const [card] = cardsOf(entries);
    expect(card.tasks.map((t) => t.status)).toEqual(["completed", "in_progress"]);
    expect(card.done).toBe(false);
  });

  it("does not move for a call that leaves the list as it was", () => {
    const listed = [{ id: "1", content: "A", status: "in_progress" }];
    const items = [create("1", "A"), update("1", "A", "in_progress"), tool("read_file"), tool("task_list", {}, listed), agent("still on it")];
    const entries = fold(items);
    expect(entries.map((e) => e.kind)).toEqual(["task_card", "tool_run", "agent"]);
  });

  it("folds a finished list into a done line where it finished", () => {
    const items = [create("1", "A"), update("1", "A", "completed"), agent("All done.")];
    const entries = fold(items);
    expect(entries.map((e) => e.kind)).toEqual(["task_card", "agent"]);
    expect(cardsOf(entries)[0]).toMatchObject({ done: true });
  });

  it("keeps a finished list's line and shows the card again further down when the list grows", () => {
    const items = [create("1", "A"), update("1", "A", "completed"), agent("done"), create("2", "B")];
    const cards = cardsOf(fold(items));
    expect(cards.map((c) => c.done)).toEqual([true, false]);
    expect(cards[1].tasks).toHaveLength(2);
  });

  it("follows the list into a later turn", () => {
    const items = [{ id: id(), kind: "user", text: "go" } as LogItem, create("1", "A"), agent("half"), { id: id(), kind: "user", text: "more" } as LogItem, update("1", "A", "in_progress")];
    const turns = groupTurns(items);
    const cards = turns.map((turn) => cardsOf(foldTaskCard(groupToolRuns(turn.items), turn.taskPlaces)));
    expect(cards.map((c) => c.length)).toEqual([0, 1]);
    expect(cards[1][0].tasks[0].status).toBe("in_progress");
  });

  it("keeps the calls around a task call in runs of their own", () => {
    const entries = fold([tool("list_files"), create("1", "A"), tool("read_file")]);
    expect(entries.map((e) => e.kind)).toEqual(["tool_run", "task_card", "tool_run"]);
  });
});
