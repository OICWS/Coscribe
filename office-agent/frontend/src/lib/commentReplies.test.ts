import { describe, expect, it } from "vitest";
import type { LogItem } from "../state/reducer";
import { answerFor } from "./commentReplies";

const user = (text: string, turnIndex: number): LogItem => ({ id: `u${turnIndex}`, kind: "user", text, turnIndex });
const agent = (id: string, text: string, streaming = false): LogItem => ({ id, kind: "agent", text, streaming });

describe("a comment's answer", () => {
  it("is the last thing coscribe said in that comment's turn", () => {
    const items = [
      user("hi", 0),
      agent("a", "hello"),
      user("Comment: x", 1),
      agent("b", "Looking."),
      agent("c", "Done: shorter title."),
      user("next", 2),
      agent("d", "later"),
    ];
    expect(answerFor(items, "Comment: x", 0)).toBe("Done: shorter title.");
  });

  it("waits while the message is not in the log or still streaming", () => {
    expect(answerFor([user("hi", 0)], "Comment: x", 0)).toBeNull();
    expect(answerFor([user("Comment: x", 0), agent("a", "Do", true)], "Comment: x", 0)).toBeNull();
  });

  it("finds the message sent after the given point, not an earlier same one", () => {
    const items = [user("Comment: x", 0), agent("a", "old"), user("Comment: x", 1), agent("b", "new")];
    expect(answerFor(items, "Comment: x", 2)).toBe("new");
  });
});
