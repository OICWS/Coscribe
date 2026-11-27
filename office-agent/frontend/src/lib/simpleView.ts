import { asksThePerson } from "../state/folderAccess";
import type { LogItem } from "../state/reducer";
import type { TurnEntry } from "./taskCard";
import { activityOf, blockedWriteOf, groupHasPendingApproval, isRunning, type ConversationActivity, type ToolRunGroup, type Turn } from "./transcriptGrouping";

/** The simple conversation view (Settings > General > Appearance) draws a turn without its tool
 * rows and in-between narration: the cards a person answers or reads stay, a running turn shows
 * one status line, and the reply shows once the turn ends. The transcript itself is unchanged, so
 * the detailed view still shows every step. */

/** The turn is held up by something the person has to answer, which says more than a status line. */
export function waitsOnThePerson(turn: Turn): boolean {
  return (
    turn.hasPendingApproval ||
    turn.items.some((item) => asksThePerson(item) || (item.kind === "plan" && item.status === "pending"))
  );
}

/** Which of a turn's entries the simple view draws. A tool run stays only while it holds an
 * approval, which is never hidden, or a write a folder refused, whose card offers access; the
 * model's words only as the finished turn's reply, since until the turn ends any of them may be
 * narration before another call. */
export function simpleEntries(entries: TurnEntry[], live: boolean, finalAgentItem: LogItem | null): TurnEntry[] {
  return entries.filter((entry) => {
    if (entry.kind === "tool_run") return groupHasPendingApproval(entry) || entry.items.some((item) => blockedWriteOf(item) !== null);
    if (entry.kind === "agent") return !live && entry === finalAgentItem;
    return true;
  });
}

/** A run waiting on an approval, as the simple view draws it: the calls the person must answer,
 * without the finished ones before them in the same run. */
export function onlyPendingApprovals(group: ToolRunGroup): ToolRunGroup {
  return { ...group, items: group.items.filter((item) => item.kind === "approval" && item.status === "pending") };
}

/** The status line's words: the latest running call's activity, or Thinking between calls. */
export function currentActivity(items: LogItem[], connectorTools: ReadonlySet<string>): ConversationActivity {
  const running = items.findLast(
    (item): item is Extract<LogItem, { kind: "tool" | "approval" }> =>
      (item.kind === "tool" || item.kind === "approval") && isRunning(item, true),
  );
  return running ? activityOf(running, connectorTools) : "Thinking";
}
