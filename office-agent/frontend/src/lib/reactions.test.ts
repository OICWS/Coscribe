import { describe, expect, it } from "vitest";
import type { LogItem } from "../state/reducer";
import { isLoneEmoji, takeReaction } from "./reactions";

const user: LogItem = { id: "u", kind: "user", text: "no need", turnIndex: 0 };
const react = (extra: Partial<Extract<LogItem, { kind: "tool" }>> = {}): LogItem => ({
  id: "r",
  kind: "tool",
  toolName: "react_to_message",
  arguments: { emoji: "👍" },
  ...extra,
});

describe("takeReaction", () => {
  it("takes the call out of the turn and gives its emoji", () => {
    expect(takeReaction([user, react({ result: "Reacted." })])).toEqual({ items: [user], reaction: "👍" });
  });

  it("waits for the call's result", () => {
    expect(takeReaction([user, react()]).reaction).toBeNull();
  });

  it("finds one made through use_tool", () => {
    const viaUseTool = react({ result: "Reacted.", toolName: "use_tool",
      arguments: { name: "react_to_message", arguments: { emoji: "🙏" } } });
    expect(takeReaction([user, viaUseTool]).reaction).toBe("🙏");
  });

  it("leaves a failed call as a row and shows no reaction", () => {
    const failed = react({ result: "bad", isError: true });
    expect(takeReaction([user, failed])).toEqual({ items: [user, failed], reaction: null });
  });

  const reply = (text: string, streaming = false): LogItem => ({ id: `a-${text}`, kind: "agent", text, streaming });

  it("takes a lone emoji written as the whole reply as the reaction", () => {
    expect(takeReaction([user, reply(" 👍 ")])).toEqual({ items: [user], reaction: "👍" });
  });

  it("drops the emoji written beside the call", () => {
    expect(takeReaction([user, react({ result: "Reacted.", arguments: { emoji: "🙏" } }), reply("👍")]))
      .toEqual({ items: [user], reaction: "🙏" });
  });

  it("keeps a lone emoji that follows other work, or that is still streaming, as a reply", () => {
    const tool = react({ toolName: "read_file", arguments: {}, result: "x" });
    expect(takeReaction([user, tool, reply("👍")]).reaction).toBeNull();
    expect(takeReaction([user, reply("👍", true)]).reaction).toBeNull();
  });

  it("keeps words as a reply", () => {
    for (const text of ["OK 👍", "👍👍", "ok", "1"]) expect(takeReaction([user, reply(text)]).reaction).toBeNull();
  });

  it("sees a joined or skin-toned emoji as one", () => {
    for (const emoji of ["❤️", "👍🏽", "👨‍👩‍👧"]) expect(isLoneEmoji(emoji)).toBe(true);
  });
});
