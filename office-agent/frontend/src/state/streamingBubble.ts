import type { LogItem } from "./reducer";

/** Finalizes a still-streaming agent bubble left behind mid-turn, such as narration a model
 * (DeepSeek, GLM) emits right before a tool call. Only "agent_delta"/"agent_message" mark a bubble
 * streaming: false, and "agent_message" only looks at the *last* item: once a "tool_result",
 * "approval_required" or "question_required" takes that slot, the bubble can't be found again and
 * its cursor never clears. Call this immediately before pushing any item that isn't itself
 * continuing that streaming bubble. */
export function closeStreamingBubble(items: LogItem[]): LogItem[] {
  const last = items[items.length - 1];
  if (!last || last.kind !== "agent" || !last.streaming) return items;
  const closed = [...items];
  closed[closed.length - 1] = { ...last, streaming: false };
  return closed;
}
