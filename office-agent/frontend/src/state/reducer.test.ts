import { describe, expect, it } from "vitest";
import type { ApprovalRequiredEvent, HistoryEntry, QuestionSpec, StateEvent } from "../types/wire";
import {
  TASK_DRAFT_SAVED_PREFIX,
  chatReducer,
  historyToItems,
  initialChatState,
  type ChatAction,
  type ChatState,
  type LogItem,
} from "./reducer";

type Of<K extends LogItem["kind"]> = Extract<LogItem, { kind: K }>;

function stateWith(patch: Partial<ChatState> = {}): ChatState {
  return { ...initialChatState, ...patch };
}
function run(state: ChatState, ...actions: ChatAction[]): ChatState {
  return actions.reduce(chatReducer, state);
}

const user = (id: string, text: string, turnIndex: number): Of<"user"> => ({ id, kind: "user", text, turnIndex });
const agentItem = (id: string, text: string, streaming: boolean): Of<"agent"> => ({
  id,
  kind: "agent",
  text,
  streaming,
});
const toolItem = (id: string, toolName: string, rest: Partial<Of<"tool">> = {}): Of<"tool"> => ({
  id,
  kind: "tool",
  toolName,
  arguments: {},
  ...rest,
});
const approvalItem = (id: string, status: Of<"approval">["status"], rest: Partial<Of<"approval">> = {}): Of<"approval"> => ({
  id,
  kind: "approval",
  toolName: "write_file",
  arguments: {},
  status,
  ...rest,
});

const question: QuestionSpec = {
  question: "Which?",
  header: "Pick",
  options: [{ label: "A", description: "" }],
  multi_select: false,
};

describe("state", () => {
  const event: StateEvent = {
    type: "state",
    plan_mode: true,
    accept_edits: true,
    auto_mode: true,
    model: "m1",
    effort: "medium",
    effort_runs_as: "low",
    context_window: 1000,
    enabled_skills: ["s1"],
    workspace_root: "C:\\work",
    folders: ["C:\\work", "C:\\other"],
    connector_tools: ["gmail_send"],
    workspace_explicit: true,
  };

  it("replaces every thread setting at once", () => {
    const next = run(stateWith(), event);
    expect(next).toMatchObject({
      planMode: true,
      acceptEdits: true,
      autoMode: true,
      model: "m1",
      contextWindow: 1000,
      enabledSkills: ["s1"],
      workspaceRoot: "C:\\work",
      workspaceExplicit: true,
      folders: ["C:\\work", "C:\\other"],
    });
    expect(next.connectorTools).toEqual(new Set(["gmail_send"]));
  });

  it("defaults auto mode off and connector tools to none for an older server", () => {
    const older = { ...event, auto_mode: undefined, connector_tools: undefined } as unknown as StateEvent;
    const next = run(stateWith({ autoMode: true, connectorTools: new Set(["x"]) }), older);
    expect(next.autoMode).toBe(false);
    expect(next.connectorTools.size).toBe(0);
  });

  it("takes turn_in_flight only when the server sends it", () => {
    expect(run(stateWith({ turnInFlight: true }), event).turnInFlight).toBe(true);
    expect(run(stateWith({ turnInFlight: true }), { ...event, turn_in_flight: false }).turnInFlight).toBe(false);
    expect(run(stateWith(), { ...event, turn_in_flight: true }).turnInFlight).toBe(true);
  });
});

describe("history and older messages", () => {
  const entries: HistoryEntry[] = [
    { kind: "user", text: "q1" },
    { kind: "agent", text: "a1" },
    { kind: "user", text: "q2", images: ["img.png"] },
    { kind: "steer", text: "also this" },
    { kind: "tool", tool_name: "read_file", arguments: { path: "a.txt" }, result: "x", is_error: false },
  ];

  it("replaces the log, numbers user turns from zero and marks history received", () => {
    const next = run(
      stateWith({ items: [user("old", "stale", 0)], workflowTest: { done: 1, total: 2 } }),
      { type: "history", entries, has_older: true },
    );
    expect(next.historyReceived).toBe(true);
    expect(next.workflowTest).toBeNull();
    expect(next.olderStatus).toBe("idle");
    expect(next.items.map((i) => i.kind)).toEqual(["user", "agent", "user", "steer", "tool"]);
    expect(next.items.filter((i): i is Of<"user"> => i.kind === "user").map((i) => i.turnIndex)).toEqual([0, 1]);
    expect(next.items[3]).toMatchObject({ kind: "steer", status: "delivered" });
    expect(next.items[4]).toMatchObject({ kind: "tool", toolName: "read_file", result: "x", isError: false });
  });

  it("leaves older status at none when the thread has nothing earlier", () => {
    expect(run(stateWith(), { type: "history", entries: [], has_older: false }).olderStatus).toBe("none");
  });

  it("restores a plan from exit_plan_mode with the answer the user gave", () => {
    const planEntry = (result: string): HistoryEntry => ({
      kind: "tool",
      tool_name: "exit_plan_mode",
      arguments: { plan: "Do it" },
      result,
      is_error: false,
    });
    const status = (result: string) => historyToItems([planEntry(result)])[0];
    expect(status("The user switched to auto mode")).toMatchObject({ kind: "plan", plan: "Do it", status: "auto" });
    expect(status("The user approved the plan")).toMatchObject({ kind: "plan", status: "manual" });
    expect(status("The user wants changes")).toMatchObject({ kind: "plan", status: "revise" });
  });

  it("restores a scheduled-task draft as saved only when the result starts with the saved prefix", () => {
    const draftEntry = (result: unknown): HistoryEntry => ({
      kind: "tool",
      tool_name: "create_scheduled_task",
      arguments: { name: "Daily" },
      result,
      is_error: false,
    });
    expect(historyToItems([draftEntry(`${TASK_DRAFT_SAVED_PREFIX} as "Daily"`)])[0]).toMatchObject({
      kind: "task_draft",
      status: "saved",
      draft: { name: "Daily" },
    });
    expect(historyToItems([draftEntry("The user dismissed it")])[0]).toMatchObject({ status: "dismissed" });
    expect(historyToItems([draftEntry(null)])[0]).toMatchObject({ status: "dismissed" });
  });

  it("prepends each revealed batch before earlier ones, read-only with turnIndex -1", () => {
    const first = run(stateWith({ olderStatus: "loading" }), {
      type: "older_messages",
      entries: [{ kind: "user", text: "u" }, { kind: "agent", text: "a" }],
      has_more: true,
    });
    const second = run(first, {
      type: "older_messages",
      entries: [
        { kind: "steer", text: "s" },
        { kind: "tool", tool_name: "t", arguments: {}, result: 1, is_error: true },
      ],
      has_more: false,
    });
    expect(first.olderStatus).toBe("idle");
    expect(first.olderItems[0]).toMatchObject({ kind: "user", turnIndex: -1 });
    expect(second.olderItems.map((i) => i.kind)).toEqual(["steer", "tool", "user", "agent"]);
    expect(second.olderItems[1]).toMatchObject({ isError: true });
    expect(second.olderStatus).toBe("no_more");
  });

  it("stops offering more once a batch comes back empty, without touching items", () => {
    const base = stateWith({ olderStatus: "loading", items: [user("u", "x", 0)] });
    const next = run(base, { type: "older_messages", entries: [], has_more: true });
    expect(next.olderStatus).toBe("no_more");
    expect(next.olderItems).toEqual([]);
    expect(next.items).toBe(base.items);
  });

  it("does not stack a second load request on one in flight", () => {
    const loading = stateWith({ olderStatus: "loading" });
    expect(run(loading, { type: "local_request_older_messages" })).toBe(loading);
    expect(run(stateWith({ olderStatus: "idle" }), { type: "local_request_older_messages" }).olderStatus).toBe(
      "loading",
    );
  });
});

describe("thread and connection resets", () => {
  it("clears the older-history cursor on a new connection and keeps the log", () => {
    const items = [user("u", "x", 0)];
    const next = run(stateWith({ historyReceived: true, olderStatus: "no_more", olderItems: items, items }), {
      type: "local_connection_reset",
    });
    expect(next).toMatchObject({ historyReceived: false, olderStatus: "none", olderItems: [] });
    expect(next.items).toBe(items);
  });

  it("keeps the settings on screen but drops the conversation when switching thread", () => {
    const connectorTools = new Set(["a"]);
    const next = run(
      stateWith({
        model: "m",
        contextWindow: 9,
        enabledSkills: ["s"],
        connectorTools,
        workspaceRoot: "W",
        workspaceExplicit: true,
        folders: ["W"],
        turnTick: 4,
        items: [user("u", "x", 0)],
        totalTokens: 50,
        turnInFlight: true,
        error: "boom",
        planMode: true,
        historyReceived: true,
        olderStatus: "idle",
        olderItems: [user("o", "y", -1)],
      }),
      { type: "local_switch_thread" },
    );
    expect(next).toMatchObject({
      model: "m",
      contextWindow: 9,
      enabledSkills: ["s"],
      workspaceRoot: "W",
      workspaceExplicit: true,
      folders: ["W"],
      turnTick: 4,
      items: [],
      totalTokens: 0,
      turnInFlight: false,
      error: null,
      planMode: false,
      historyReceived: false,
      olderStatus: "none",
      olderItems: [],
    });
    expect(next.connectorTools).toBe(connectorTools);
  });
});

describe("user messages", () => {
  it("adds the user bubble, starts a turn and clears the last error", () => {
    const next = run(stateWith({ error: "old", items: [user("u0", "a", 0), agentItem("a0", "b", false)] }), {
      type: "local_user_message",
      text: "hello",
      instant: false,
      images: ["i.png"],
    });
    expect(next.turnInFlight).toBe(true);
    expect(next.error).toBeNull();
    expect(next.items.at(-1)).toMatchObject({ kind: "user", text: "hello", turnIndex: 1, images: ["i.png"] });
  });

  it("leaves turn-in-flight alone for an instant command", () => {
    expect(run(stateWith(), { type: "local_user_message", text: "/plan", instant: true }).turnInFlight).toBe(false);
    expect(
      run(stateWith({ turnInFlight: true }), { type: "local_user_message", text: "/plan", instant: true })
        .turnInFlight,
    ).toBe(true);
  });

  it("numbers a server-started turn after the user items already there", () => {
    const base = stateWith({ items: [user("u0", "a", 0), agentItem("a0", "b", false), user("u1", "c", 1)] });
    for (const action of [
      { type: "turn_started", text: "report" },
      { type: "scheduled_run_started", text: "run" },
    ] as const) {
      const next = run(base, action);
      expect(next.turnInFlight).toBe(true);
      expect(next.items.at(-1)).toMatchObject({ kind: "user", text: action.text, turnIndex: 2 });
    }
  });

  it("turn_started also clears the error", () => {
    expect(run(stateWith({ error: "x" }), { type: "turn_started", text: "t" }).error).toBeNull();
  });
});

describe("edit and rewind", () => {
  const items: LogItem[] = [
    user("u0", "first", 0),
    agentItem("a0", "r0", false),
    user("u1", "second", 1),
    agentItem("a1", "r1", false),
  ];

  it("cuts the log at the edited turn and appends the new text with the same index", () => {
    const next = run(stateWith({ items, error: "x" }), { type: "local_edit_message", turnIndex: 1, text: "edited" });
    expect(next.items).toHaveLength(3);
    expect(next.items.slice(0, 2)).toEqual(items.slice(0, 2));
    expect(next.items[2]).toMatchObject({ kind: "user", text: "edited", turnIndex: 1 });
    expect(next.turnInFlight).toBe(true);
    expect(next.error).toBeNull();
  });

  it("keeps the whole log and appends when the edited turn is unknown", () => {
    const next = run(stateWith({ items }), { type: "local_edit_message", turnIndex: 9, text: "edited" });
    expect(next.items).toHaveLength(5);
  });

  it("rewinds by truncating without appending and without starting a turn", () => {
    const next = run(stateWith({ items }), { type: "local_rewind_message", turnIndex: 1 });
    expect(next.items).toEqual(items.slice(0, 2));
    expect(next.turnInFlight).toBe(false);
  });

  it("ignores a rewind to a turn that does not exist", () => {
    const base = stateWith({ items });
    expect(run(base, { type: "local_rewind_message", turnIndex: 5 })).toBe(base);
  });

  it("treats the server's rewound confirmation as a no-op", () => {
    const base = stateWith({ items });
    expect(run(base, { type: "rewound", index: 1 })).toBe(base);
  });
});

describe("streaming", () => {
  it("starts a streaming bubble, then appends deltas to it", () => {
    const next = run(
      stateWith(),
      { type: "agent_delta", text: "Hel" },
      { type: "agent_delta", text: "lo" },
    );
    expect(next.items).toHaveLength(1);
    expect(next.items[0]).toMatchObject({ kind: "agent", text: "Hello", streaming: true });
  });

  it("starts a new bubble after a finished agent message", () => {
    const next = run(stateWith({ items: [agentItem("a", "done", false)] }), { type: "agent_delta", text: "more" });
    expect(next.items).toHaveLength(2);
    expect(next.items[1]).toMatchObject({ text: "more", streaming: true });
  });

  it("finishes the streaming bubble with the final text, ends the turn and clears the workflow test", () => {
    const next = run(
      stateWith({ turnInFlight: true, workflowTest: { done: 1, total: 2 } }),
      { type: "agent_delta", text: "partial" },
      { type: "agent_message", text: "full answer" },
    );
    expect(next.items).toHaveLength(1);
    expect(next.items[0]).toMatchObject({ text: "full answer", streaming: false });
    expect(next.turnInFlight).toBe(false);
    expect(next.workflowTest).toBeNull();
  });

  it("adds a bubble for an agent message with nothing streaming", () => {
    const next = run(stateWith({ items: [user("u", "q", 0)] }), { type: "agent_message", text: "hi" });
    expect(next.items.at(-1)).toMatchObject({ kind: "agent", text: "hi", streaming: false });
  });

  it("closes a streaming bubble left behind when a tool starts", () => {
    const next = run(stateWith({ items: [agentItem("a", "narration", true)] }), {
      type: "tool_started",
      tool_name: "read_file",
      arguments: { path: "x" },
    });
    expect(next.items[0]).toMatchObject({ streaming: false });
    expect(next.items[1]).toMatchObject({ kind: "tool", toolName: "read_file", arguments: { path: "x" } });
    expect(next.items[1]).not.toHaveProperty("result");
  });

  it("closes the bubble on error and stops the turn", () => {
    const next = run(stateWith({ turnInFlight: true, items: [agentItem("a", "half", true)] }), {
      type: "error",
      message: "boom",
    });
    expect(next.items[0]).toMatchObject({ streaming: false });
    expect(next.error).toBe("boom");
    expect(next.turnInFlight).toBe(false);
  });

  it("does not copy the log when there is no streaming bubble to close", () => {
    const items = [agentItem("a", "done", false)];
    expect(run(stateWith({ items }), { type: "error", message: "x" }).items).toBe(items);
  });
});

describe("tool results", () => {
  it("fills in the newest started call of the same tool", () => {
    const next = run(
      stateWith({
        items: [
          toolItem("t1", "read_file", { result: "first" }),
          toolItem("t2", "read_file"),
          toolItem("t3", "list_files"),
        ],
      }),
      { type: "tool_result", tool_name: "read_file", arguments: { path: "b" }, result: "second", is_error: true },
    );
    expect(next.items).toHaveLength(3);
    expect(next.items[1]).toMatchObject({
      id: "t2",
      arguments: { path: "b" },
      result: "second",
      isError: true,
    });
    expect(next.items[0]).toMatchObject({ result: "first" });
    expect(next.items[2]).not.toHaveProperty("result");
  });

  it("does not mutate the log it was given", () => {
    const items = [toolItem("t", "read_file")];
    run(stateWith({ items }), { type: "tool_result", tool_name: "read_file", arguments: {}, result: 1, is_error: false });
    expect(items[0]).not.toHaveProperty("result");
  });

  it("puts the result of an approved call on its approval item instead of adding a second one", () => {
    const next = run(stateWith({ items: [approvalItem("ap", "approved", { beforePreview: "b.png" })] }), {
      type: "tool_result",
      tool_name: "write_file",
      arguments: { path: "n.txt" },
      result: { ok: true },
      is_error: false,
    });
    expect(next.items).toHaveLength(1);
    expect(next.items[0]).toMatchObject({
      kind: "approval",
      id: "ap",
      status: "approved",
      beforePreview: "b.png",
      arguments: { path: "n.txt" },
      result: { ok: true },
      isError: false,
    });
  });

  it("does not put a result on an approval that is still pending or was denied", () => {
    for (const status of ["pending", "denied"] as const) {
      const next = run(stateWith({ items: [approvalItem("ap", status)] }), {
        type: "tool_result",
        tool_name: "write_file",
        arguments: {},
        result: "r",
        is_error: false,
      });
      expect(next.items).toHaveLength(2);
      expect(next.items[0]).not.toHaveProperty("result");
      expect(next.items[1]).toMatchObject({ kind: "tool", result: "r" });
    }
  });

  it("adds a finished tool item when nothing matches", () => {
    const next = run(stateWith(), {
      type: "tool_result",
      tool_name: "read_file",
      arguments: { path: "x" },
      result: "r",
      is_error: false,
    });
    expect(next.items).toEqual([
      { id: expect.any(String), kind: "tool", toolName: "read_file", arguments: { path: "x" }, result: "r", isError: false },
    ]);
  });

  it("closes a streaming bubble before the result lands", () => {
    const next = run(stateWith({ items: [agentItem("a", "text", true)] }), {
      type: "tool_result",
      tool_name: "read_file",
      arguments: {},
      result: "r",
      is_error: false,
    });
    expect(next.items[0]).toMatchObject({ streaming: false });
  });

  it("clears the running workflow test only when test_workflow returns", () => {
    const busy = stateWith({ workflowTest: { done: 1, total: 3 } });
    const other = run(busy, { type: "tool_result", tool_name: "read_file", arguments: {}, result: 1, is_error: false });
    const test = run(busy, { type: "tool_result", tool_name: "test_workflow", arguments: {}, result: 1, is_error: false });
    expect(other.workflowTest).toEqual({ done: 1, total: 3 });
    expect(test.workflowTest).toBeNull();
  });
});

describe("approvals", () => {
  it("adds a pending approval under the server's id, with previews and the reviewer note", () => {
    const next = run(stateWith({ items: [agentItem("a", "about to write", true)] }), {
      type: "approval_required",
      id: "ap-1",
      tool_name: "write_file",
      arguments: { path: "x" },
      before_preview: "b.png",
      after_preview: "a.png",
      reviewer_note: "touches a shared folder",
    });
    expect(next.items[0]).toMatchObject({ streaming: false });
    expect(next.items[1]).toEqual({
      id: "ap-1",
      kind: "approval",
      toolName: "write_file",
      arguments: { path: "x" },
      status: "pending",
      beforePreview: "b.png",
      afterPreview: "a.png",
      reviewerNote: "touches a shared folder",
    });
  });

  it("defaults the reviewer note to null", () => {
    const next = run(stateWith(), {
      type: "approval_required",
      id: "ap",
      tool_name: "write_file",
      arguments: {},
      before_preview: null,
      after_preview: null,
    } as Omit<ApprovalRequiredEvent, "reviewer_note"> as ChatAction);
    expect(next.items[0]).toMatchObject({ reviewerNote: null });
  });

  it("leaves the chat alone for a sub-agent's approval", () => {
    const base = stateWith({ items: [agentItem("a", "t", true)] });
    const next = run(base, {
      type: "approval_required",
      id: "ap",
      tool_name: "write_file",
      arguments: {},
      before_preview: null,
      after_preview: null,
      reviewer_note: null,
      subagent_id: "sub-1",
    });
    expect(next).toBe(base);
  });

  it("marks only the matching approval approved or denied", () => {
    const base = stateWith({
      items: [approvalItem("ap1", "pending"), approvalItem("ap2", "pending"), toolItem("ap1x", "write_file")],
    });
    const approved = run(base, { type: "local_approval_resolved", id: "ap1", approved: true });
    const denied = run(base, { type: "local_approval_resolved", id: "ap2", approved: false });
    expect(approved.items.map((i) => (i.kind === "approval" ? i.status : i.kind))).toEqual([
      "approved",
      "pending",
      "tool",
    ]);
    expect(denied.items.map((i) => (i.kind === "approval" ? i.status : i.kind))).toEqual([
      "pending",
      "denied",
      "tool",
    ]);
  });
});

describe("questions, plans and task drafts", () => {
  it("adds a pending question under the server's id and closes the bubble", () => {
    const next = run(stateWith({ items: [agentItem("a", "t", true)] }), {
      type: "question_required",
      id: "q1",
      questions: [question],
    });
    expect(next.items[0]).toMatchObject({ streaming: false });
    expect(next.items[1]).toEqual({ id: "q1", kind: "question", questions: [question], status: "pending" });
  });

  it("records the answers only on the matching question", () => {
    const base = run(
      stateWith(),
      { type: "question_required", id: "q1", questions: [question] },
      { type: "question_required", id: "q2", questions: [question] },
    );
    const next = run(base, { type: "local_question_answered", id: "q1", answers: ["A", null] });
    expect(next.items[0]).toMatchObject({ status: "answered", answers: ["A", null] });
    expect(next.items[1]).toMatchObject({ status: "pending" });
    expect(run(base, { type: "local_question_answered", id: "q1", answers: null }).items[0]).toMatchObject({
      status: "answered",
      answers: null,
    });
  });

  it("adds a pending plan and records how it was answered", () => {
    const pending = run(stateWith({ items: [agentItem("a", "t", true)] }), {
      type: "plan_ready",
      id: "p1",
      plan: "Step 1",
    });
    expect(pending.items[0]).toMatchObject({ streaming: false });
    expect(pending.items[1]).toEqual({ id: "p1", kind: "plan", plan: "Step 1", status: "pending" });
    const answered = run(pending, { type: "local_plan_answered", id: "p1", status: "auto" });
    expect(answered.items[1]).toMatchObject({ status: "auto" });
    expect(run(pending, { type: "local_plan_answered", id: "other", status: "auto" }).items[1]).toMatchObject({
      status: "pending",
    });
  });

  it("adds a pending task draft and records saving under the name the user chose", () => {
    const pending = run(stateWith({ items: [agentItem("a", "t", true)] }), {
      type: "task_draft_required",
      id: "d1",
      draft: { name: "Daily" },
    });
    expect(pending.items[0]).toMatchObject({ streaming: false });
    expect(pending.items[1]).toEqual({ id: "d1", kind: "task_draft", draft: { name: "Daily" }, status: "pending" });
    const saved = run(pending, { type: "local_task_draft_resolved", id: "d1", status: "saved", savedName: "Renamed" });
    expect(saved.items[1]).toMatchObject({ status: "saved", savedName: "Renamed" });
    const dismissed = run(pending, { type: "local_task_draft_resolved", id: "d1", status: "dismissed" });
    expect(dismissed.items[1]).toMatchObject({ status: "dismissed", savedName: undefined });
  });
});

describe("usage", () => {
  it("records the token total and the cache stats when the provider reports them", () => {
    const next = run(stateWith(), {
      type: "usage",
      total_tokens: 1200,
      cache_read_tokens: 800,
      input_tokens: 1000,
      cache_hit_rate: 0.8,
    });
    expect(next.totalTokens).toBe(1200);
    expect(next.cacheStats).toEqual({ cacheReadTokens: 800, inputTokens: 1000, hitRate: 0.8 });
  });

  it("keeps the earlier cache stats when a call reports none, and keeps a genuine zero", () => {
    const withStats = stateWith({ cacheStats: { cacheReadTokens: 1, inputTokens: 2, hitRate: 0.5 } });
    expect(run(withStats, { type: "usage", total_tokens: 5 }).cacheStats).toEqual(withStats.cacheStats);
    const zero = run(stateWith(), {
      type: "usage",
      total_tokens: 5,
      cache_read_tokens: 0,
      input_tokens: 10,
      cache_hit_rate: 0,
    });
    expect(zero.cacheStats).toEqual({ cacheReadTokens: 0, inputTokens: 10, hitRate: 0 });
  });

  it("keeps the earlier cache stats when only some of the three fields arrive", () => {
    const withStats = stateWith({ cacheStats: { cacheReadTokens: 1, inputTokens: 2, hitRate: 0.5 } });
    const next = run(withStats, { type: "usage", total_tokens: 9, cache_read_tokens: 4, input_tokens: 8 });
    expect(next.cacheStats).toEqual(withStats.cacheStats);
  });
});

describe("system notes and turn end", () => {
  it("appends a compaction note with the elapsed time, and ends the turn", () => {
    const fast = run(stateWith({ turnInFlight: true }), { type: "compacted", before: 40, after: 6, elapsed_ms: 850 });
    const slow = run(stateWith(), { type: "compacted", before: 40, after: 6, elapsed_ms: 2500 });
    expect(fast.turnInFlight).toBe(false);
    expect(fast.items[0]).toMatchObject({ kind: "system", text: "Compacted 40 messages down to 6 · 850ms." });
    expect(slow.items[0]).toMatchObject({ text: "Compacted 40 messages down to 6 · 2.5s." });
  });

  it("replaces the whole log with one note when cleared", () => {
    const next = run(stateWith({ turnInFlight: true, items: [user("u", "x", 0), agentItem("a", "y", false)] }), {
      type: "cleared",
    });
    expect(next.items).toEqual([{ id: expect.any(String), kind: "system", text: "Cleared this thread's conversation history." }]);
    expect(next.turnInFlight).toBe(false);
  });

  it("confirms a saved skill and ends the turn", () => {
    const next = run(stateWith({ turnInFlight: true }), { type: "skill_saved", name: "Weekly report", slug: "weekly" });
    expect(next.items[0]).toMatchObject({
      kind: "system",
      text: 'Saved skill "Weekly report" -- try /weekly to use it directly.',
    });
    expect(next.turnInFlight).toBe(false);
  });

  it("bumps the refetch tick and ends the turn when tasks change", () => {
    const next = run(stateWith({ turnInFlight: true, turnTick: 2, workflowTest: { done: 1, total: 2 } }), {
      type: "tasks_changed",
    });
    expect(next).toMatchObject({ turnInFlight: false, turnTick: 3, workflowTest: null });
  });

  it("tracks workflow test progress", () => {
    expect(run(stateWith(), {
      type: "workflow_test_progress",
      tool_call_id: "c",
      step: "s",
      status: "done",
      done: 2,
      total: 5,
    }).workflowTest).toEqual({ done: 2, total: 5 });
  });

  it("leaves state alone for events App.tsx handles itself", () => {
    const base = stateWith({ items: [user("u", "x", 0)] });
    expect(run(base, { type: "thread_titled", title: "t" })).toBe(base);
    expect(run(base, { type: "subagents_changed", task_id: "t", status: "done" })).toBe(base);
  });
});

describe("steering notes", () => {
  it("adds a pending note", () => {
    const next = run(stateWith(), { type: "local_steer", id: "s1", text: "also this" });
    expect(next.items).toEqual([{ id: "s1", kind: "steer", text: "also this", status: "pending" }]);
  });

  it("withdraws only the listed notes", () => {
    const base = run(
      stateWith({ items: [user("u", "x", 0)] }),
      { type: "local_steer", id: "s1", text: "a" },
      { type: "local_steer", id: "s2", text: "b" },
    );
    const next = run(base, { type: "local_steers_withdrawn", ids: ["s1"] });
    expect(next.items.map((i) => i.id)).toEqual(["u", "s2"]);
  });

  it("marks the listed notes delivered", () => {
    const base = run(
      stateWith(),
      { type: "local_steer", id: "s1", text: "a" },
      { type: "local_steer", id: "s2", text: "b" },
    );
    const next = run(base, { type: "steers_delivered", ids: ["s2"] });
    expect(next.items.map((i) => (i.kind === "steer" ? i.status : null))).toEqual(["pending", "delivered"]);
  });

  it("replaces requeued notes with one user message and starts a turn", () => {
    const base = run(
      stateWith({ items: [user("u", "x", 0)] }),
      { type: "local_steer", id: "s1", text: "a" },
      { type: "local_steer", id: "s2", text: "b" },
      { type: "local_steer", id: "s3", text: "c" },
    );
    const next = run(base, { type: "steers_requeued", ids: ["s1", "s2"], text: "a\nb" });
    expect(next.turnInFlight).toBe(true);
    expect(next.items.map((i) => i.id)).toEqual(["u", "s3", next.items[2].id]);
    expect(next.items[2]).toMatchObject({ kind: "user", text: "a\nb", turnIndex: 1 });
  });
});
