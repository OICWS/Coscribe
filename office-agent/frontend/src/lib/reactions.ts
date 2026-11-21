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

const graphemes = new Intl.Segmenter(undefined, { granularity: "grapheme" });

/** One emoji and nothing else, as a person sees it: a single grapheme that is a pictograph. */
export function isLoneEmoji(text: string): boolean {
  const trimmed = text.trim();
  if (!/\p{Extended_Pictographic}/u.test(trimmed)) return false;
  const iterator = graphemes.segment(trimmed)[Symbol.iterator]();
  return !iterator.next().done && iterator.next().done === true;
}

function isLoneEmojiReply(item: LogItem): item is Extract<LogItem, { kind: "agent" }> {
  return item.kind === "agent" && !item.streaming && isLoneEmoji(item.text);
}

/** A turn's items without the model's reaction calls, and the emoji it answered the user's message
 * with: a reaction shows on that message, not as a tool row. A failed call stays a row.
 *
 * A model sometimes writes the emoji as its whole reply instead of calling the tool, or writes it
 * beside the call; when the turn holds nothing else, that reply is the reaction too. A lone emoji
 * after other work stays a reply: it may answer a question card, not the user's message. */
export function takeReaction(items: LogItem[]): { items: LogItem[]; reaction: string | null } {
  let reaction: string | null = null;
  const rest = items.filter((item) => {
    const emoji = reactionOf(item);
    if (emoji === null) return true;
    reaction = emoji;
    return false;
  });
  const replies = rest.filter((item) => item.kind !== "user");
  if (replies.length === 0 || !replies.every(isLoneEmojiReply)) return { items: rest, reaction };
  return { items: rest.filter((item) => item.kind === "user"), reaction: reaction ?? replies[replies.length - 1].text.trim() };
}
