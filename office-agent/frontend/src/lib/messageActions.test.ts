import { describe, expect, it } from "vitest";
import type { LogItem } from "../state/reducer";
import { fullTime, messagesLeavingChanges } from "./messageActions";

const user = (turnIndex: number): LogItem => ({ id: `u${turnIndex}`, kind: "user", text: "q", turnIndex });
const call = (toolName: string, args: Record<string, unknown> = {}, extra: Partial<{ isError: boolean; result: unknown }> = { result: "ok" }): LogItem => ({
  id: toolName,
  kind: "tool",
  toolName,
  arguments: args,
  ...extra,
});

describe("which messages a rewind would leave changes after", () => {
  it("marks every message before a call that wrote a file, and none after it", () => {
    const items = [user(0), call("read_file"), user(1), call("write_docx"), user(2), call("search_files")];
    expect([...messagesLeavingChanges(items)].sort()).toEqual([0, 1]);
  });

  it("counts commands, connector actions and calls through use_tool", () => {
    expect(messagesLeavingChanges([user(0), call("run_python_script")]).has(0)).toBe(true);
    expect(messagesLeavingChanges([user(0), call("notion_create_page")]).has(0)).toBe(true);
    expect(messagesLeavingChanges([user(0), call("use_tool", { name: "edit_file" })]).has(0)).toBe(true);
  });

  it("ignores reads, the task list, failed calls and calls still waiting", () => {
    const items = [user(0), call("read_xlsx"), call("task_create"), call("write_file", {}, { isError: true, result: "x" }), call("edit_file", {}, {})];
    expect(messagesLeavingChanges(items).size).toBe(0);
  });
});

describe("the full time under a relative one", () => {
  it("is empty for a time it can't read", () => {
    expect(fullTime("not a time")).toBe("");
  });
});
