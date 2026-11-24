import { useEffect, useLayoutEffect, useRef } from "react";
import { groupToolRuns, groupTurns, currentWorkflowDrafts, draftsInTheWorks, workflowTests, type WorkflowDraftEntry } from "../lib/transcriptGrouping";
import { type LogItem } from "../state/reducer";
import { useFollowEnd } from "../lib/useFollowEnd";
import { type PptxShapeCapture } from "./PptxShapeOverlay";
import { type PlanChoice, type PlanItem } from "./PlanCard";
import { type FolderActions } from "./folderActions";
import { type DraftCards } from "./workflow";
import { type TaskDraftItem } from "./chatlog/index";
import { MessageActionsContext, NO_CONNECTOR_TOOLS } from "./chatlog/index";
import { useMessageActions } from "../lib/messageActions";
import { ChatContexts } from "./chatlog/index";
import { ToolRunGroupView } from "./chatlog/index";
import { TurnView, LogItemView } from "./chatlog/index";

interface ChatLogProps {
  items: LogItem[];
  /** A reply is being generated -- its tool calls without a result yet
   * are shown as running. */
  turnInFlight?: boolean;
  /** The connected connectors' tool names, counted as "used N tools". */
  connectorTools?: ReadonlySet<string>;
  onApprove: (id: string, approved: boolean, scope?: "task") => void;
  onAnswerPlan?: (item: PlanItem, choice: PlanChoice, feedback: string) => void;
  onOpenPlan?: () => void;
  /** Edit a sent message and run from it. Undefined while a turn is in flight, which it would race. */
  onEditMessage?: (turnIndex: number, text: string) => void;
  /** Take a sent message and what follows out of the conversation. Undefined while a turn is in flight. */
  onRewindMessage?: (turnIndex: number, text: string) => void;
  /** True until this thread's history has arrived -- an existing
   * thread shows a spinner then, not the brand-new-thread greeting. */
  loading: boolean;
  onReviewTaskDraft: (item: TaskDraftItem) => void;
  onDismissTaskDraft: (item: TaskDraftItem) => void;
  onReviewWorkflowDraft?: (entry: WorkflowDraftEntry) => void;
  /** Workflow draft cards' other buttons, and what they show. */
  draftCards?: Pick<DraftCards, "saved" | "testProgress" | "onTestAgain" | "onContinue" | "onOpenTask">;
  /** What the card under a refused script write can do. */
  folderActions?: FolderActions;
  /** A shape clicked in a pptx preview (PptxShapeOverlay) -- threaded up
   * to App.tsx exactly like BrowserPanel's own onSendToChat. */
  onPptxShapePicked: (capture: PptxShapeCapture) => void;
  /** Earlier, pre-/compact messages revealed by scrolling near the top
   * of the log -- kept as a separate list rendered above `items` rather
   * than prepended into it, see ChatState.olderItems' own comment for
   * why. Always read-only (no Rewind or Edit: the server's history
   * starts after the compaction), and rendered as plain turns via the same
   * groupTurns pass `items` gets, so a pre-compact turn looks identical
   * to a live one apart from that. */
  olderItems: LogItem[];
  olderStatus: "none" | "idle" | "loading" | "no_more";
  onLoadOlder: () => void;
}

/** How close to the top of the scroll container (in px) counts as "the
 * user is looking at the oldest thing currently loaded" -- real, live-
 * reported preference: a manual "Load earlier messages" button read as
 * unnecessary friction, the user wanted plain scroll-up-to-load-more
 * like every other chat product. A small, nonzero threshold (rather
 * than exactly 0) means the load kicks in a little before the user
 * actually hits the physical top, so the prepend (and its own scroll-
 * anchoring, below) has already landed by the time they'd notice. */
const SCROLL_LOAD_OLDER_THRESHOLD_PX = 150;

export function ChatLog({
  items,
  onApprove,
  onAnswerPlan, onOpenPlan,
  onEditMessage,
  onRewindMessage,
  loading,
  onReviewTaskDraft,
  onDismissTaskDraft,
  onReviewWorkflowDraft,
  draftCards,
  folderActions,
  onPptxShapePicked,
  olderItems,
  olderStatus,
  onLoadOlder,
  turnInFlight = false,
  connectorTools = NO_CONNECTOR_TOOLS,
}: ChatLogProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const turns = groupTurns(items);
  const olderTurns = groupTurns(olderItems);
  const allItems = [...olderItems, ...items];
  const cards: DraftCards = {
    saved: new Map(),
    testProgress: null,
    ...draftCards,
    currentDraftIds: new Set(currentWorkflowDrafts(allItems).map((d) => d.id)),
    inTheWorks: draftsInTheWorks(allItems, turnInFlight),
    tests: workflowTests(allItems, turnInFlight),
    onReview: onReviewWorkflowDraft,
  };

  const messageActions = useMessageActions(items, turnInFlight, onEditMessage, onRewindMessage);
  const onScroll = useFollowEnd(scrollRef, endRef, items, items[items.length - 1]?.kind === "user");
  // Revealing older history above never moves the viewport (see the scroll-anchoring effect
  // below, which handles that case on its own terms).

  // Keeps whatever the user was already looking at pinned in place when
  // a new batch of older messages is prepended above it -- without this,
  // the browser's own default scroll-anchoring is inconsistent across a
  // prepend this large (a whole turn's worth of new DOM nodes above the
  // current scrollTop), and the viewport visibly jumps. Captures height
  // *before* the prepend (in onLoadOlder's own caller, App.tsx, via the
  // ref read here at layout time -- scrollHeight already reflects the
  // old, pre-prepend DOM on this effect's first run for a given
  // olderItems change) and restores the equivalent scrollTop after.
  const prevOlderScrollHeight = useRef<number | null>(null);
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (prevOlderScrollHeight.current !== null) {
      el.scrollTop += el.scrollHeight - prevOlderScrollHeight.current;
    }
    prevOlderScrollHeight.current = el.scrollHeight;
  }, [olderItems]);

  // Auto-loads on scroll-up instead of a manual button -- a ref (not
  // onLoadOlder in the dependency array) holds the latest callback so
  // this effect only re-subscribes when olderStatus itself actually
  // changes, not on every unrelated parent re-render (App.tsx's
  // onLoadOlderMessages is a fresh closure each render); without that,
  // a render happening to land while still "idle" and still scrolled
  // near the top would fire a duplicate load before the first one's own
  // "loading" status had a chance to propagate back down and stop it.
  // Checks once immediately on entering "idle" (not just on a scroll
  // event) so a thread short enough that its content doesn't even fill
  // the viewport -- already effectively "at the top" -- still loads
  // without requiring an actual scroll gesture first.
  const onLoadOlderRef = useRef(onLoadOlder);
  onLoadOlderRef.current = onLoadOlder;
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || olderStatus !== "idle") return;
    const checkAndLoad = () => {
      if (el.scrollTop < SCROLL_LOAD_OLDER_THRESHOLD_PX) onLoadOlderRef.current();
    };
    checkAndLoad();
    el.addEventListener("scroll", checkAndLoad);
    return () => el.removeEventListener("scroll", checkAndLoad);
  }, [olderStatus]);

  if (items.length === 0) {
    return (
      <div data-testid="chat-log" className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex h-full items-center justify-center">
            <div
              className="h-6 w-6 animate-spin rounded-full border-[3px] border-[color-mix(in_srgb,var(--fg)_15%,transparent)] border-t-[var(--accent)] motion-reduce:animate-none"
              role="status"
              aria-label="Loading conversation"
            />
          </div>
        )}
      </div>
    );
  }

  return (
    <ChatContexts connectorTools={connectorTools} folderActions={folderActions ?? null} cards={cards} items={items} olderItems={olderItems}>
    <div data-testid="chat-log" className="flex-1 overflow-y-auto" ref={scrollRef} onScroll={onScroll}>
      <div className="mx-auto flex w-full max-w-[880px] flex-col gap-3 px-4 py-4">
        {olderStatus === "loading" && (
          <p className="self-center text-xs text-[var(--muted)]">Loading earlier messages...</p>
        )}
        {olderTurns.map((turn, i) => (
          // Read-only: the server's history starts after the compaction, so these can't be cut.
          <TurnView
            key={turn.id}
            turn={turn}
            compactAfter={i === olderTurns.length - 1 && items[0]?.kind === "system" && items[0].text.startsWith("Context compacted")}
            onApprove={onApprove}
            onPptxShapePicked={() => {}}
          />
        ))}
        <MessageActionsContext.Provider value={messageActions}>
          {turns.map((turn, i) => (
            <TurnView
              key={turn.id}
              turn={turn}
              onApprove={onApprove}
              onAnswerPlan={onAnswerPlan} onOpenPlan={onOpenPlan}
              onReviewTaskDraft={onReviewTaskDraft}
              onDismissTaskDraft={onDismissTaskDraft}
              live={turnInFlight && i === turns.length - 1}
              onPptxShapePicked={onPptxShapePicked}
            />
          ))}
        </MessageActionsContext.Provider>
        <div ref={endRef} />
      </div>
    </div>
    </ChatContexts>
  );
}

/** A read-only transcript -- a sub-agent's, in the Background tasks panel --
 * drawn with the chat's own components. `live` shows its last call as
 * running. */
export function TranscriptItems({
  items,
  live,
  onApprove,
}: {
  items: LogItem[];
  live: boolean;
  onApprove: (id: string, approved: boolean, scope?: "task") => void;
}) {
  const entries = groupToolRuns(items);
  return (
    <div className="flex flex-col gap-3">
      {entries.map((entry) =>
        entry.kind === "tool_run" ? (
          <ToolRunGroupView
            key={entry.id}
            group={entry}
            live={live}
            onApprove={onApprove}
            onPptxShapePicked={() => {}}
          />
        ) : entry.kind === "agent" ? (
          <LogItemView key={entry.id} item={entry} />
        ) : null,
      )}
    </div>
  );
}
