import { lazy, Suspense } from "react";
import { groupToolRuns, type Turn } from "../../lib/transcriptGrouping";
import { type LogItem } from "../../state/reducer";
import { CopyButton } from "../CopyButton";
import { RetryIcon, RewindIcon } from "../icons";
import { type PptxShapeCapture } from "../PptxShapeOverlay";
import { PlanCard, type PlanChoice, type PlanItem } from "../PlanCard";
import { QuestionRecord } from "../QuestionCard";
import { INVESTIGATION_PREFIX, InvestigationCard, RUN_PROMPT_PREFIX, ScheduledRunCard } from "../ScheduledRunCard";
import { CONVERSATION_MESSAGE_PREFIX, ConversationMessageCard } from "../ConversationMessageCard";
import { SUBAGENT_REPORT_PREFIX, SubAgentReportCard } from "../SubAgentReportCard";
import { TaskDraftCard } from "../TaskDraftCard";
import { WorkflowDraftCard } from "../workflow/WorkflowDraftCard";
import { type TaskDraftItem } from "./types";
import { ToolRunGroupView } from "./ToolRuns";
import { UserMessageView, SteerView } from "./UserMessageView";
import { OpenFileChips } from "./OpenFileChips";

/** react-markdown + remark/rehype + katex is the single biggest dependency
 * added to this app (roughly triples the production bundle) -- code-split
 * it into its own chunk so a session that never renders a markdown-heavy
 * reply doesn't pay for it on first load. The Suspense fallback is the
 * plain, unparsed text (what the agent bubble looked like before this
 * feature existed), so the one-time chunk fetch shows real text, not a
 * spinner or blank bubble. */
const Markdown = lazy(() => import("../Markdown").then((m) => ({ default: m.Markdown })));

/** Renders one turn's items (via the same groupToolRuns pass the whole
 * thread used to go through directly) plus, once the turn is actually
 * done, a bottom-left copy+retry+rewind+relative-time footer -- replaces
 * the old one-CopyButton-per-agent-message placement (see ROADMAP.md's
 * Phase 8am items 7-8). "Done" means: has a final agent reply that isn't
 * still streaming, and no approval in this turn is still waiting on the
 * user -- the same real backend rule handle_edit_message/
 * handle_rewind_message both enforce ("Resolve the pending approval
 * before editing/rewinding"), so neither button is ever offered
 * somewhere it would just come back as a WS error.
 *
 * Retry and Rewind are two different operations, previously conflated
 * under one "Rewind" button that actually retried (real, live-reported
 * bug): Retry truncates the turn and immediately resubmits the same
 * question (onEditMessage with unedited text) -- same question, new
 * answer. Rewind truncates and stops there, handing the original
 * question text back to the composer instead (onRewindMessage) -- an
 * undo, with no new answer generated. Retry gets its own RetryIcon (a
 * two-arrowhead refresh cycle) rather than RewindIcon mirrored --
 * explicit correction: a single arc flipped horizontally still read as
 * "the same arrow, unclear which way" at 14px and was mistaken for
 * Rewind in real use, not a clear inverse.
 *
 * Both restricted to `isLastTurn` -- explicit correction: every past turn
 * used to offer this, but reaching back to an earlier turn while later
 * ones already exist is exactly what "edit an earlier message" (the
 * pencil icon on the user bubble itself, still available on every turn)
 * already does more explicitly; a second, identically-named affordance on
 * every turn read as "jump to any point," which isn't what either of
 * these do (both only ever discard everything *after* the turn clicked,
 * same as edit). The whole footer is also hover-only (opacity-0, revealed
 * via the turn's own group/turn on hover) instead of permanently visible
 * -- matches the rest of this app's hover-reveal convention for secondary
 * actions (ThreadRow's "..." menu, the user bubble's own edit pencil)
 * rather than a footer under every single reply, always on screen. */
export function TurnView({
  turn,
  isLastTurn = false,
  onApprove,
  onAnswerPlan,
  onEditMessage,
  onRewindMessage,
  onReviewTaskDraft,
  onDismissTaskDraft,
  live = false,
  onPptxShapePicked,
}: {
  turn: Turn;
  isLastTurn?: boolean;
  /** This turn is the one a reply is still being generated for. */
  live?: boolean;
  onApprove: (id: string, approved: boolean, scope?: "task") => void;
  onAnswerPlan?: (item: PlanItem, choice: PlanChoice, feedback: string) => void;
  onEditMessage?: (turnIndex: number, text: string) => void;
  onRewindMessage?: (turnIndex: number, text: string) => void;
  onReviewTaskDraft?: (item: TaskDraftItem) => void;
  onDismissTaskDraft?: (item: TaskDraftItem) => void;
  onPptxShapePicked: (capture: PptxShapeCapture) => void;
}) {
  const entries = groupToolRuns(turn.items);
  const finalAgentItem = turn.finalAgentItem;
  const userItem = turn.userItem;
  const canFooter =
    finalAgentItem !== null && userItem !== null && !finalAgentItem.streaming && !turn.hasPendingApproval;

  return (
    <div className="group/turn flex flex-col gap-3">
      {/* groupToolRuns now always wraps a tool/approval run into a
       * ToolRunGroup, even a run of one (see its own comment) -- a bare
       * "tool"/"approval" LogItem can no longer reach this map at all,
       * so there's no case for it here anymore. */}
      {entries.map((entry) =>
        entry.kind === "tool_run" ? (
          <ToolRunGroupView
            key={entry.id}
            group={entry}
            live={live}
            onApprove={onApprove}
            onPptxShapePicked={onPptxShapePicked}
          />
        ) : entry.kind === "question" ? (
          entry.status === "answered" ? <QuestionRecord key={entry.id} item={entry} /> : null
        ) : entry.kind === "plan" ? (
          <PlanCard key={entry.id} item={entry} onAnswer={onAnswerPlan} />
        ) : entry.kind === "task_draft" ? (
          <TaskDraftCard key={entry.id} item={entry} onReview={onReviewTaskDraft} onDismiss={onDismissTaskDraft} />
        ) : entry.kind === "workflow_draft" ? (
          <WorkflowDraftCard key={entry.id} entry={entry} />
        ) : entry.kind === "steer" ? (
          <SteerView key={entry.id} item={entry} />
        ) : (
          <LogItemView key={entry.id} item={entry} onEditMessage={isLastTurn ? onEditMessage : undefined} />
        ),
      )}
      <OpenFileChips items={entries.flatMap((entry) => (entry.kind === "tool_run" ? entry.items : []))} />
      {canFooter && (
        <div className="-mt-2 flex items-center gap-0.5 self-start opacity-0 transition-opacity group-hover/turn:opacity-100">
          <CopyButton
            getText={() => finalAgentItem.text}
            title="Copy reply"
            className="flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
          />
          {onEditMessage && isLastTurn && (
            <button
              type="button"
              title="Retry -- ask this again"
              className="flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
              onClick={() => onEditMessage(userItem.turnIndex, userItem.text)}
            >
              <RetryIcon className="h-3.5 w-3.5" />
            </button>
          )}
          {onRewindMessage && isLastTurn && (
            <button
              type="button"
              title="Rewind -- undo this question"
              className="flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
              onClick={() => onRewindMessage(userItem.turnIndex, userItem.text)}
            >
              <RewindIcon className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export function LogItemView({
  item,
  onEditMessage,
}: {
  item: Extract<LogItem, { kind: "user" | "agent" | "system" }>;
  onEditMessage?: (turnIndex: number, text: string) => void;
}) {
  if (item.kind === "user") {
    if (item.text.startsWith(RUN_PROMPT_PREFIX)) return <ScheduledRunCard text={item.text} />;
    if (item.text.startsWith(INVESTIGATION_PREFIX)) return <InvestigationCard text={item.text} />;
    if (item.text.startsWith(SUBAGENT_REPORT_PREFIX)) return <SubAgentReportCard text={item.text} />;
    if (item.text.startsWith(CONVERSATION_MESSAGE_PREFIX)) return <ConversationMessageCard text={item.text} />;
    return <UserMessageView item={item} onEditMessage={onEditMessage} />;
  }

  if (item.kind === "agent") {
    const text = item.streaming ? `${item.text} ▍` : item.text;
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
      </div>
    );
  }

  return (
    <div className="self-start text-xs text-[var(--muted)]">
      {item.text}
      <span className="ml-0.5">&rsaquo;</span>
    </div>
  );
}
