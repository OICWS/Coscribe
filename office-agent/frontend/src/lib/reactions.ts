import type { LogItem } from "../state/reducer";

const REACTION_TOOL = "react_to_message";

function reactionOf(item: LogItem): string | null {
  // Only once it worked: a call that fails stays a row, and the model is told why.
  if (item.kind !== "tool" || item.result === undefined || item.isError) return null;
  const inner = item.arguments.name;
  const viaUseTool = item.toolName === "use_tool" && inner === REACTION_TOOL;
  if (item.toolName !== REACTION_TOOL && !viaUseTool) return null;
  const args = viaUseTool ? item.arguments.arguments : item.arguments;
  const emoji = args && typeof args === "object" ? (args as Record<string, unknown>).emoji : undefined;
  return typeof emoji === "string" && emoji.trim() !== "" ? emoji.trim() : null;
}

/** A turn's items without the model's reaction calls, and the emoji it answered the user's message
 * with: a reaction shows on that message, not as a tool row. A failed call stays a row. */
export function takeReaction(items: LogItem[]): { items: LogItem[]; reaction: string | null } {
  let reaction: string | null = null;
  const rest = items.filter((item) => {
    const emoji = reactionOf(item);
    if (emoji === null) return true;
    reaction = emoji;
    return false;
  });
  return { items: rest, reaction };
}
