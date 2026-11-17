import { describe, expect, it } from "vitest";
import { chatReducer, initialChatState, type ChatState, type ChatAction, type LogItem } from "./reducer";
const stateWith = (patch: Partial<ChatState> = {}): ChatState => ({ ...initialChatState, ...patch });
const run = (state: ChatState, ...actions: ChatAction[]) => actions.reduce(chatReducer, state);
const user = (id: string, text: string, turnIndex: number): LogItem => ({ id, kind: "user", text, turnIndex });

describe("compaction", () => {
  it("preserves messages and adds only one compact divider", () => {
    const started = run(
      stateWith({ items: [user("u", "hi", 0)] }),
      { type: "local_user_message", text: "/compact", instant: true },
      { type: "local_compact_started", startedAt: 1000 },
    );
    expect(started.turnInFlight).toBe(false);
    expect(started.compaction).toEqual({ status: "running", startedAt: 1000 });
    const done = run(started, { type: "compacted", before: 40, after: 6, elapsed_ms: 2500, tokens_saved: 123400 });
    expect(done.compaction).toBeNull();
    expect(done.olderItems).toEqual(started.items);
    expect(done.items.at(-1)).toMatchObject({ kind: "system", text: "Context compacted · ~123,400 tokens saved" });
    expect(run(done, { type: "local_user_message", text: "next", instant: false }).compaction).toBeNull();
  });

  it("clears a running compact status on error or reconnection", () => {
    const started = run(stateWith(), { type: "local_compact_started", startedAt: 1000 });
    expect(run(started, { type: "error", message: "failed" }).compaction).toBeNull();
    expect(run(started, { type: "local_connection_reset" }).compaction).toBeNull();
    expect(run(started, { type: "cleared" }).compaction).toBeNull();
  });

  it("restores original image messages before the divider and keeps automatic turns running", () => {
    const replay = run(stateWith(), { type: "history", has_older: true,
      entries: [{ kind: "system", text: "Context compacted" }],
      older_entries: [{ kind: "user", text: "original", images: ["data:image/png;base64,x"] }] });
    expect(replay.olderItems[0]).toMatchObject({ kind: "user", text: "original", turnIndex: -1, images: ["data:image/png;base64,x"] });
    const live = run({ ...replay, turnInFlight: true }, { type: "compacted", before: 40, after: 6, elapsed_ms: 0, automatic: true, retained_user_turns: 3 });
    expect(live.turnInFlight).toBe(true);
    expect(live.compaction).toBeNull();
    expect(run(live, { type: "local_user_message", text: "next", instant: false }).items.at(-1)).toMatchObject({ turnIndex: 3 });
  });

});
