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
    expect(planPanelData([create("1", "A"), ...plans])).toEqual({
      tasks: [{ id: "1", content: "A", status: "pending" }],
      plan: "second",
      pendingPlanId: plans[1].id,
    });
    expect(planPanelData([agent()])).toEqual({ tasks: [], plan: null, pendingPlanId: null });
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

describe("background tasks on the card", () => {
  const card = (items: LogItem[]) => {
    const cards = cardsOf(fold(items));
    return cards[cards.length - 1];
  };

  it("binds a background task to the item in progress when it started", () => {
    const items = [
      create("1", "Research"),
      update("1", "Research", "in_progress"),
      tool("spawn_agent_background", { prompt: "look" }, { task_id: "agent-1", status: "running" }),
      tool("run_background_script", { script: "x" }, JSON.stringify({ task_id: "script-1" })),
    ];
    expect(card(items).bound).toEqual({ "1": ["agent-1", "script-1"] });
  });

  it("binds a starter whose call was approved first", () => {
    const approved: Of<"approval"> = {
      id: id(),
      kind: "approval",
      toolName: "run_background_script",
      arguments: { language: "python", script: "x" },
      status: "approved",
      result: { task_id: "script-9", status: "running" },
    };
    const items = [create("1", "Crunch"), update("1", "Crunch", "in_progress"), approved];
    expect(card(items).bound).toEqual({ "1": ["script-9"] });
  });

  it("binds a script that moved to the background, and not one that ran to its end", () => {
    const items = [
      create("1", "Crunch"),
      update("1", "Crunch", "in_progress"),
      tool("run_python_script", { script: "x" }, { status: "running_in_background", task_id: "moved-1" }),
      tool("run_python_script", { script: "y" }, { returncode: 0, task_id: "not-a-task" }),
    ];
    expect(card(items).bound).toEqual({ "1": ["moved-1"] });
  });

  it("binds nothing before the starter's result is in, or with no item in progress", () => {
    const pending = [create("1", "A"), update("1", "A", "in_progress"), tool("spawn_agent_background", { prompt: "p" })];
    expect(card(pending).bound).toEqual({});
    const idle = [create("1", "A"), tool("spawn_agent_background", { prompt: "p" }, { task_id: "agent-1" })];
    expect(card(idle).bound).toEqual({});
  });

  it("gives a task started while two items run to the one that started last", () => {
    const items = [
      create("1", "A"),
      create("2", "B"),
      update("1", "A", "in_progress"),
      update("2", "B", "in_progress"),
      tool("run_background_command", { command: "build" }, { task_id: "cmd-1" }),
      update("2", "B", "completed"),
      tool("run_background_command", { command: "test" }, { task_id: "cmd-2" }),
    ];
    expect(card(items).bound).toEqual({ "2": ["cmd-1"], "1": ["cmd-2"] });
  });

  it("keeps an item's tasks when the card moves on in a later turn", () => {
    const items = [
      create("1", "A"),
      update("1", "A", "in_progress"),
      tool("spawn_agent_background", { prompt: "p" }, { task_id: "agent-1" }),
      agent("waiting on it"),
      create("2", "B"),
    ];
    expect(card(items).bound).toEqual({ "1": ["agent-1"] });
  });
});

describe("an approved plan whose list the person edited", () => {
  const plan = (tasks?: { id: string; content: string; status: "pending" | "completed" }[]): Of<"plan"> => ({
    id: id(),
    kind: "plan",
    plan: "# Plan",
    status: tasks ? "auto" : "pending",
    ...(tasks && { tasks }),
  });

  it("replaces the list, and later calls apply to the new one", () => {
    const edited = [
      { id: "2", content: "Write it short", status: "pending" as const },
      { id: "3", content: "Send", status: "pending" as const },
    ];
    const items = [create("1", "Read"), create("2", "Write"), plan(edited), update("3", "Send", "completed")];
    expect(taskListOf(items)).toEqual([edited[0], { ...edited[1], status: "completed" }]);
  });

  it("puts the card under the plan when that was the last change", () => {
    const approved = plan([{ id: "1", content: "Read", status: "pending" }]);
    const items = [create("1", "Read"), create("2", "Write"), approved];
    const entries = fold(items);
    const at = entries.findIndex((entry) => entry.id === approved.id);
    expect(entries[at + 1]).toMatchObject({ kind: "task_card", tasks: [{ id: "1", content: "Read" }] });
  });

  it("names the plan that waits for an answer", () => {
    const waiting = plan();
    expect(planPanelData([create("1", "Read"), waiting]).pendingPlanId).toBe(waiting.id);
    expect(planPanelData([create("1", "Read"), plan([])]).pendingPlanId).toBeNull();
  });
});
