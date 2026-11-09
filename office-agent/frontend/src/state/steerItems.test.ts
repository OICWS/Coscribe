import { describe, expect, it } from "vitest";
import { chatReducer, initialChatState, type ChatAction, type ChatState, type LogItem } from "./reducer";

function stateWith(patch: Partial<ChatState> = {}): ChatState {
  return { ...initialChatState, ...patch };
}
function run(state: ChatState, ...actions: ChatAction[]): ChatState {
  return actions.reduce(chatReducer, state);
}
const user = (id: string, text: string, turnIndex: number): LogItem => ({ id, kind: "user", text, turnIndex });

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
    const next = run(base, { type: "steers_requeued", ids: ["s1", "s2"], text: "a\n\nb" });
    expect(next.turnInFlight).toBe(true);
    expect(next.items.map((i) => i.id)).toEqual(["u", "s3", next.items[2].id]);
    expect(next.items[2]).toMatchObject({ kind: "user", text: "a\n\nb", turnIndex: 1 });
  });

  it("keeps a note's pictures and files when it is pending and when it is requeued", () => {
    const base = run(
      stateWith(),
      { type: "local_steer", id: "s1", text: "look", outgoingText: "look (files)", images: ["data:image/png;base64,AA"], files: ["a.pdf"] },
      { type: "local_steer", id: "s2", text: "and this", images: ["data:image/png;base64,BB"] },
    );
    expect(base.items[0]).toMatchObject({ kind: "steer", status: "pending", images: ["data:image/png;base64,AA"], files: ["a.pdf"] });
    const next = run(base, { type: "steers_requeued", ids: ["s1", "s2"], text: "look (files)\n\nand this" });
    expect(next.items).toHaveLength(1);
    expect(next.items[0]).toMatchObject({
      kind: "user",
      text: "look\n\nand this",
      images: ["data:image/png;base64,AA", "data:image/png;base64,BB"],
      files: ["a.pdf"],
    });
  });

  it("shows the server's text for notes another tab sent", () => {
    const next = run(stateWith(), { type: "steers_requeued", ids: ["elsewhere"], text: "from another tab" });
    expect(next.items[0]).toMatchObject({ kind: "user", text: "from another tab" });
    expect(next.items[0]).not.toHaveProperty("images");
  });
});
