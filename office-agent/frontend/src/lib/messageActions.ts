import { useMemo } from "react";
import type { LogItem } from "../state/reducer";
import { WAITING_ON_PERSON } from "./sessionSignals";

/** What a sent message's own Rewind and Edit, and its reply's Fork, do, and whether they can run now. */
export interface MessageActions {
  rewind: (turnIndex: number, text: string) => void;
  edit: (turnIndex: number, text: string) => void;
  /** Copies the conversation up to that message's reply into a new one; absent where it can't. */
  fork?: (turnIndex: number) => void;
  /** Why neither can run now, or null when both can. The server refuses both mid-turn and while
   * an approval or a question waits, since either would race the history it truncates. */
  blocked: string | null;
  /** The messages whose later turns did something a rewind leaves in place, by turnIndex. */
  leavesChanges: ReadonlySet<number>;
}

// A rewind only cuts the conversation: what these calls did to files, the computer or a connected
// service stays. Matched by verb because connector tools are named per service.
const CHANGES = /_(write|edit|modify|add|set|format|recalc|delete|remove|move|rename|copy|apply|run|download|install|uninstall|duplicate|reorder|insert|replace|send|create|update|post|upload|spawn)_/;
// Changes to the conversation's own task list, which the rewind takes back with it.
const CONVERSATION_ONLY = /^task_/;

function realName(item: { toolName: string; arguments: Record<string, unknown> }): string {
  const inner = item.arguments.name;
  return item.toolName === "use_tool" && typeof inner === "string" ? inner : item.toolName;
}

function leftAChange(item: LogItem): boolean {
  if (item.kind !== "tool" && item.kind !== "approval") return false;
  if (item.result === undefined || item.isError) return false;
  const name = realName(item);
  return !CONVERSATION_ONLY.test(name) && CHANGES.test(`_${name}`);
}

/** The turnIndex of every user message from which on some call changed a file, ran code or acted
 * on a connected service. */
export function messagesLeavingChanges(items: LogItem[]): Set<number> {
  const marked = new Set<number>();
  let changedAfter = false;
  for (let i = items.length - 1; i >= 0; i--) {
    const item = items[i];
    if (leftAChange(item)) changedAfter = true;
    if (item.kind === "user" && changedAfter) marked.add(item.turnIndex);
  }
  return marked;
}

/** "Nov 18, 2026, 4:33 AM": the full time a relative one stands for. */
export function fullTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
}

/** The sent messages' Rewind and Edit for the chat: disabled while a reply runs or something waits
 * on the person; null where the chat offers neither. */
export function useMessageActions(
  items: LogItem[],
  turnInFlight: boolean,
  edit: MessageActions["edit"] | undefined,
  rewind: MessageActions["rewind"] | undefined,
  fork?: MessageActions["fork"],
): MessageActions | null {
  const leavesChanges = useMemo(() => messagesLeavingChanges(items), [items]);
  if (edit && rewind) {
    return { edit, rewind, fork, blocked: items.some(WAITING_ON_PERSON) ? "Answer the open request first" : null, leavesChanges };
  }
  return turnInFlight ? { edit: () => {}, rewind: () => {}, blocked: "Unavailable while working", leavesChanges } : null;
}
