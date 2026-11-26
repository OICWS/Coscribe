import { lazy, Suspense, useState } from "react";
import { foldTaskCard } from "../../lib/taskCard";
import { groupToolRuns, type Turn } from "../../lib/transcriptGrouping";
import { takeReaction } from "../../lib/reactions";
import { useAppearance } from "../../lib/appearance";
import { groupHasPendingApproval } from "../../lib/transcriptGrouping";
import { onlyPendingApprovals, simpleEntries, waitsOnThePerson } from "../../lib/simpleView";
import { type LogItem } from "../../state/reducer";
import { CopyButton } from "../CopyButton";
import { type PptxShapeCapture } from "../PptxShapeOverlay";
import { PlanCard, type PlanChoice, type PlanItem } from "../PlanCard";
import { AskCard, PendingQuestionCard } from "./QuestionCards";
import { isAnswerMessage } from "../../lib/questionCards";
import {
  INVESTIGATION_PREFIX,
  InvestigationCard,
  REVISION_PREFIX,
  RUN_PROMPT_PREFIX,
  ScheduledRunCard,
} from "../ScheduledRunCard";
import { CONVERSATION_MESSAGE_PREFIX, ConversationMessageCard } from "../ConversationMessageCard";
import { BACKGROUND_REPORT_PREFIX, BackgroundTaskReportCard } from "../BackgroundTaskReportCard";
import { SUBAGENT_REPORT_PREFIX, SubAgentReportCard } from "../SubAgentReportCard";
import { TaskDraftCard } from "../TaskDraftCard";
import { TaskCard } from "./TaskCard";
import { WorkflowDraftCard } from "../workflow";
import { CONNECTED_NOTE_PREFIX, ConnectorConnectedNote, ConnectorOfferCard } from "./ConnectorOfferCard";
import { FolderAccessCard } from "./FolderAccessCard";
import { PackageInstallCard } from "./PackageInstallCard";
import { asksThePerson } from "../../state/folderAccess";
import { type TaskDraftItem } from "./types";
import { ToolRunGroupView } from "./ToolRuns";
import { BlockedWriteCards, SimpleStatus } from "./SimpleView";
import { UserMessageView, SteerView } from "./UserMessageView";
import { FileCards } from "./FileCards";
import { SystemCards } from "./SystemCards";
import { splitStopped } from "./helpers";
import { StoppedNote } from "./StoppedNote";
import { HoverTip } from "./HoverTip";
import { fullTime } from "../../lib/messageActions";
import { timeAgo } from "../../lib/sessionList";

/** react-markdown + remark/rehype + katex is the single biggest dependency
 * added to this app (roughly triples the production bundle) -- code-split
 * it into its own chunk so a session that never renders a markdown-heavy
 * reply doesn't pay for it on first load. The Suspense fallback is the
 * plain, unparsed text (what the agent bubble looked like before this
 * feature existed), so the one-time chunk fetch shows real text, not a
 * spinner or blank bubble. */
const Markdown = lazy(() => import("../Markdown").then((m) => ({ default: m.Markdown })));

/** One turn's items and, once its reply is done, a hover footer with Copy and when the reply
 * finished. Rewind and Edit sit on the user's message instead (UserMessageView). */
export function TurnView({
  turn,
  compactAfter = false,
  onApprove,
  onAnswerPlan,
  onOpenPlan,
  onReviewTaskDraft,
  onDismissTaskDraft,
  live = false,
  onPptxShapePicked,
}: {
  turn: Turn;
  compactAfter?: boolean;
  /** This turn is the one a reply is still being generated for. */
  live?: boolean;
  onApprove: (id: string, approved: boolean, scope?: "task") => void;
  onAnswerPlan?: (item: PlanItem, choice: PlanChoice, feedback: string) => void;
  onOpenPlan?: () => void;
  onReviewTaskDraft?: (item: TaskDraftItem) => void;
  onDismissTaskDraft?: (item: TaskDraftItem) => void;
  onPptxShapePicked: (capture: PptxShapeCapture) => void;
}) {
  // A message drawn as a card (a run's prompt, a report) has no bubble to carry an emoji.
  const plain = turn.userItem !== null && !isCardMessage(turn.userItem.text);
  const { items, reaction } = plain ? takeReaction(turn.items) : { items: turn.items, reaction: null };
  const allEntries = foldTaskCard(groupToolRuns(items), turn.taskPlaces);
  const calls = allEntries.flatMap((entry) => (entry.kind === "tool_run" ? entry.items : []));
  const waiting = turn.hasPendingApproval || turn.items.some(asksThePerson);
  // null when that reply was a lone emoji now shown as the reaction.
  const finalAgentItem = items.some((item) => item === turn.finalAgentItem) ? turn.finalAgentItem : null;
  const simple = useAppearance().conversationView === "simple";
  const entries = simple ? simpleEntries(allEntries, live, finalAgentItem) : allEntries;
  const canFooter =
    finalAgentItem !== null &&
    turn.userItem !== null &&
    !finalAgentItem.streaming &&
    !turn.hasPendingApproval &&
    splitStopped(finalAgentItem.text).said.trim() !== "";
  // Read on hover, so "2 minutes ago" is current when the footer shows.
  const [now, setNow] = useState(() => Date.now());

  return (
    <div className="group/turn relative flex flex-col gap-3" onMouseEnter={() => setNow(Date.now())}>
      {/* groupToolRuns wraps every tool or approval, even a run of one, so neither reaches here bare. */}
      {entries.map((entry) =>
        entry.kind === "tool_run" && simple && !groupHasPendingApproval(entry) ? (
          <BlockedWriteCards key={entry.id} group={entry} />
        ) : entry.kind === "tool_run" ? (
          <ToolRunGroupView
            key={entry.id}
            group={simple ? onlyPendingApprovals(entry) : entry}
            live={live}
            onApprove={onApprove}
            onPptxShapePicked={onPptxShapePicked}
          />
        ) : entry.kind === "task_card" ? (
          <TaskCard key={entry.id} entry={entry} live={live} waiting={waiting} />
        ) : entry.kind === "question" ? (
          <PendingQuestionCard key={entry.id} item={entry} />
        ) : entry.kind === "ask_card" ? (
          <AskCard key={entry.id} item={entry.item} />
        ) : entry.kind === "plan" ? (
          <PlanCard key={entry.id} item={entry} onAnswer={onAnswerPlan} onOpenPlan={onOpenPlan} />
        ) : entry.kind === "task_draft" ? (
          <TaskDraftCard key={entry.id} item={entry} onReview={onReviewTaskDraft} onDismiss={onDismissTaskDraft} />
        ) : entry.kind === "workflow_draft" ? (
          <WorkflowDraftCard key={entry.id} entry={entry} />
        ) : entry.kind === "connector_offer" ? (<ConnectorOfferCard key={entry.id} entry={entry} />
        ) : entry.kind === "folder_access" ? (<FolderAccessCard key={entry.id} item={entry} />
        ) : entry.kind === "package_install" ? (<PackageInstallCard key={entry.id} item={entry} />
        ) : entry.kind === "steer" ? (
          <SteerView key={entry.id} item={entry} />
        ) : (
          <LogItemView key={entry.id} item={entry} reaction={entry.kind === "user" ? reaction : null} />
        ),
      )}
      <FileCards items={calls} />
      <SystemCards items={calls} />
      {simple && live && !waitsOnThePerson(turn) && <SimpleStatus turn={turn} />}
      {canFooter && !(simple && live) && (
        <div className={`${compactAfter ? "absolute left-0 top-full mt-1" : "-mt-2"} flex items-center gap-0.5 self-start opacity-0 transition-opacity group-hover/turn:opacity-100`}>
          <CopyButton
            getText={() => splitStopped(finalAgentItem.text).said}
            title="Copy reply"
            className="flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
          />
          {finalAgentItem.doneAt && (
            <HoverTip label={fullTime(finalAgentItem.doneAt)}>
              <span className="ml-1 cursor-default text-xs text-[var(--muted)]">{timeAgo(finalAgentItem.doneAt, now)}</span>
            </HoverTip>
          )}
        </div>
      )}
    </div>
  );
}

const CARD_PREFIXES = [
  RUN_PROMPT_PREFIX,
  INVESTIGATION_PREFIX,
  REVISION_PREFIX,
  SUBAGENT_REPORT_PREFIX,
  BACKGROUND_REPORT_PREFIX,
  CONNECTED_NOTE_PREFIX,
  CONVERSATION_MESSAGE_PREFIX,
];

function isCardMessage(text: string): boolean {
  return CARD_PREFIXES.some((prefix) => text.startsWith(prefix)) || isAnswerMessage(text);
}

export function LogItemView({
  item,
  reaction = null,
}: {
  item: Extract<LogItem, { kind: "user" | "agent" | "system" }>;
  /** The emoji the model answered this user message with. */
  reaction?: string | null;
}) {
  if (item.kind === "user") {
    if (item.text.startsWith(RUN_PROMPT_PREFIX)) return <ScheduledRunCard text={item.text} />;
    if (item.text.startsWith(INVESTIGATION_PREFIX) || item.text.startsWith(REVISION_PREFIX))
      return <InvestigationCard text={item.text} />;
    if (item.text.startsWith(SUBAGENT_REPORT_PREFIX)) return <SubAgentReportCard text={item.text} />;
    if (item.text.startsWith(BACKGROUND_REPORT_PREFIX)) return <BackgroundTaskReportCard text={item.text} />;
    if (item.text.startsWith(CONNECTED_NOTE_PREFIX)) return <ConnectorConnectedNote text={item.text} />;
    if (item.text.startsWith(CONVERSATION_MESSAGE_PREFIX)) return <ConversationMessageCard text={item.text} />;
    // The card it answers shows the answer.
    if (isAnswerMessage(item.text)) return null;
    return <UserMessageView item={item} reaction={reaction} />;
  }

  if (item.kind === "agent") {
    const { said, stopped, running } = item.streaming ? { said: item.text, stopped: false, running: 0 } : splitStopped(item.text);
    const text = item.streaming ? `${said} ▍` : said;
    if (stopped && !said.trim()) return <StoppedNote running={running} />;
    // The server sends no words only for a turn a tool ended, an emoji on the user's message.
    if (!item.streaming && !said.trim()) return null;
    return (
      <div className="min-w-0 max-w-[92%] [overflow-wrap:anywhere]">
        {/* No border/bubble at all, like claude.ai's own assistant replies
         * -- the earlier border-l-2 "anchor" (dc76b88) was real, live
         * user feedback at the time, but became its own live complaint
         * later ("那条竖线不好看"). The muted tool-call summary line
         * directly above already reads as visually distinct from this
         * full-contrast prose without needing a line to separate them --
         * verified via screenshot, not just reasoned about. Copy used to
         * live here too (hover-revealed, per message) -- now one copy
         * button per turn instead, see TurnView's own footer. */}
        <div className="py-1 text-[var(--agent-bubble-fg)]">
          <Suspense fallback={<div className="whitespace-pre-wrap">{text}</div>}>
            <Markdown text={text} />
          </Suspense>
        </div>
        {stopped && <StoppedNote running={running} />}
      </div>
    );
  }

  if (item.text.startsWith("Context compacted")) return (
    <div role="note" className="w-full px-7 py-1 text-center text-xs text-[var(--muted)]">{item.text}</div>
  );

  return (
    <div className="self-start text-xs text-[var(--muted)]">
      {item.text}
      <span className="ml-0.5">&rsaquo;</span>
    </div>
  );
}
