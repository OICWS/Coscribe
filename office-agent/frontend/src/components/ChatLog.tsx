import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { groupToolRuns, groupTurns, latestWorkflowDraft, latestWorkflowDraftId, workflowTests, type WorkflowDraftEntry } from "../lib/transcriptGrouping";
import { type LogItem } from "../state/reducer";
import { EmptyState } from "./EmptyState";
import { type PptxShapeCapture } from "./PptxShapeOverlay";
import { type PlanChoice, type PlanItem } from "./PlanCard";
import { type FolderActions } from "./folderActions";
import { type DraftCards } from "./workflow/draftCards";
import { PinnedDraftBar } from "./workflow/WorkflowDraftCard";
import { type TaskDraftItem } from "./chatlog/types";
import { ShowDiffStats, NO_CONNECTOR_TOOLS } from "./chatlog/contexts";
import { ChatContexts } from "./chatlog/ChatContexts";
import { ToolRunGroupView } from "./chatlog/ToolRuns";
import { TurnView, LogItemView } from "./chatlog/TurnView";

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
  /** Undefined while a turn is in flight -- editing mid-turn would race
   * the very history the edit is about to truncate, so the affordance is
   * hidden entirely rather than left clickable-but-erroring. */
  onEditMessage?: (turnIndex: number, text: string) => void;
  /** Rewind (undo the last question+reply, hand the text back to the
   * composer) -- same "hidden while a turn is in flight" reasoning as
   * onEditMessage above, and offered on the same footer, see TurnView. */
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
   * why. Always read-only (no onEditMessage wired for these -- see
   * TurnView's call below), and rendered as plain turns via the same
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
    latestDraftId: latestWorkflowDraftId(allItems),
    tests: workflowTests(allItems, turnInFlight),
    onReview: onReviewWorkflowDraft,
  };
  const latestDraft = latestWorkflowDraft(allItems);
  const pinnable = latestDraft !== null && !(latestDraft.draftId && cards.saved.has(latestDraft.draftId));
  const [latestCardVisible, setLatestCardVisible] = useState(true);
  const latestCardId = pinnable ? latestDraft.id : null;

  useEffect(() => {
    const root = scrollRef.current;
    const card = latestCardId ? root?.querySelector(`[data-draft-card="${latestCardId}"]`) : null;
    if (!root || !card) {
      setLatestCardVisible(true);
      return;
    }
    const observer = new IntersectionObserver(([entry]) => setLatestCardVisible(entry.isIntersecting), {
      root,
      threshold: 0.2,
    });
    observer.observe(card);
    return () => observer.disconnect();
  }, [latestCardId, items.length]);

  const showLatestCard = () => {
    const card = latestCardId ? scrollRef.current?.querySelector(`[data-draft-card="${latestCardId}"]`) : null;
    card?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
    // Deliberately not [items, olderItems] -- appending a live item
    // should always jump to the bottom, but revealing older history
    // above should never move the viewport at all (see the scroll-
    // anchoring effect below, which handles that case on its own terms
    // instead of fighting this one for the same scroll position).
  }, [items]);

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
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <div
              className="h-6 w-6 animate-spin rounded-full border-[3px] border-[color-mix(in_srgb,var(--fg)_15%,transparent)] border-t-[var(--accent)] motion-reduce:animate-none"
              role="status"
              aria-label="Loading conversation"
            />
          </div>
        ) : (
          <EmptyState />
        )}
      </div>
    );
  }

  return (
    <ChatContexts connectorTools={connectorTools} folderActions={folderActions ?? null} cards={cards} items={items} olderItems={olderItems}>
    <div data-testid="chat-log" className="flex-1 overflow-y-auto" ref={scrollRef}>
      <div className="mx-auto flex w-full max-w-[880px] flex-col gap-3 px-4 py-4">
        {olderStatus === "loading" && (
          <p className="self-center text-xs text-[var(--muted)]">Loading earlier messages...</p>
        )}
        {olderTurns.map((turn) => (
          // No onEditMessage (read-only replay, see olderItems' own prop
          // comment) and onPptxShapePicked is a no-op -- targeting a
          // follow-up edit off a pre-compact preview isn't something
          // this pass adds a real affordance for, and TurnView requires
          // the prop regardless of whether anything's clickable.
          <TurnView
            key={turn.id}
            turn={turn}
            onApprove={onApprove}
            onPptxShapePicked={() => {}}
          />
        ))}
        {olderItems.length > 0 && <div className="border-b border-[var(--border)]" />}
        {turns.map((turn, i) => (
          <TurnView
            key={turn.id}
            turn={turn}
            isLastTurn={i === turns.length - 1}
            onApprove={onApprove}
            onAnswerPlan={onAnswerPlan} onOpenPlan={onOpenPlan}
            onEditMessage={onEditMessage}
            onRewindMessage={onRewindMessage}
            onReviewTaskDraft={onReviewTaskDraft}
            onDismissTaskDraft={onDismissTaskDraft}
            live={turnInFlight && i === turns.length - 1}
            onPptxShapePicked={onPptxShapePicked}
          />
        ))}
        <div ref={endRef} />
        {pinnable && !latestCardVisible && <PinnedDraftBar entry={latestDraft} onShow={showLatestCard} />}
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
    <ShowDiffStats.Provider value={false}>
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
    </ShowDiffStats.Provider>
  );
}
