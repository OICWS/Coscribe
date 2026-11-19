import { describe, expect, it } from "vitest";
import type { LogItem } from "../state/reducer";
import { takeReaction } from "./reactions";

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

  it("finds one made through use_tool", () => {
    const viaUseTool = react({ toolName: "use_tool", arguments: { name: "react_to_message", arguments: { emoji: "🙏" } } });
    expect(takeReaction([user, viaUseTool]).reaction).toBe("🙏");
  });

  it("leaves a failed call as a row and shows no reaction", () => {
    const failed = react({ result: "bad", isError: true });
    expect(takeReaction([user, failed])).toEqual({ items: [user, failed], reaction: null });
  });
});
