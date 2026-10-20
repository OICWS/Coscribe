import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  getDocxBytes,
  getDocxReview,
  stackCards,
  type DocxReview,
  type DocxView,
} from "../lib/docxReview";
import { openThreadFile } from "../lib/rest";
import { DocxChangeBar } from "./DocxChangeBar";
import { DocxCommentCard } from "./DocxCommentCard";
import { DocxNewComment } from "./DocxNewComment";
import { useChangeSelection, useDocxActions } from "./docxActions";
import { useDockPanel } from "./dock/dockContext";
import { ArrowDownIcon, ArrowUpIcon, ExternalLinkIcon, MessageCircleIcon } from "./icons";

const RAIL_WIDTH = 248;
const CARD_GAP = 8;
/** Below this scale beside the rail the page is too small to read: comments open in a drawer instead. */
const MIN_ZOOM_BESIDE_RAIL = 0.6;
const VIEWS: { id: DocxView; label: string }[] = [
  { id: "review", label: "Review" },
  { id: "final", label: "Final" },
  { id: "original", label: "Original" },
];

interface Anchor {
  id: string;
  range: Range;
  top: number;
  /** Where the commented words' first line ends. */
  right: number;
}

/** docx-preview leaves an HTML comment at each end of a comment's range:
 * the one place its output says which words belong to which comment. */
function commentRanges(root: HTMLElement): Map<string, Range> {
  const starts = new Map<string, Comment>();
  const ranges = new Map<string, Range>();
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_COMMENT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const marker = /^(start|end) of comment #(\S+)$/.exec(node.textContent ?? "");
    if (!marker) continue;
    if (marker[1] === "start") starts.set(marker[2], node as Comment);
    else if (starts.has(marker[2])) {
      const range = document.createRange();
      range.setStartAfter(starts.get(marker[2])!);
      range.setEndBefore(node);
      ranges.set(marker[2], range);
    }
  }
  return ranges;
}

interface Stop {
  top: number;
  comment?: string;
  el?: Element;
}

/** Each tracked change and each comment's words, with its height on the page. */
function stops(content: HTMLElement | null, page: HTMLElement | null, anchors: Anchor[]): Stop[] {
  if (!content || !page) return [];
  const origin = content.getBoundingClientRect().top;
  const changes = [...page.querySelectorAll("ins, del")].map((el) => ({
    top: el.getBoundingClientRect().top - origin,
    el,
  }));
  const comments = anchors.map((a) => ({ top: a.top, comment: a.id }));
  return [...changes, ...comments].sort((a, b) => a.top - b.top);
}

function ViewSwitch({ view, onPick }: { view: DocxView; onPick: (view: DocxView) => void }) {
  return (
    <div role="radiogroup" aria-label="View" className="flex rounded-lg bg-[var(--card-bg)] p-0.5 text-xs">
      {VIEWS.map((v) => (
        <button
          key={v.id}
          type="button"
          role="radio"
          aria-checked={view === v.id}
          className={`rounded-md px-2 py-1 ${view === v.id ? "bg-[var(--bg)] text-[var(--fg)] shadow-sm" : "text-[var(--muted)] hover:text-[var(--fg)]"}`}
          onClick={() => onPick(v.id)}
        >
          {v.label}
        </button>
      ))}
    </div>
  );
}

/** A Word file beside the conversation: its pages, its tracked changes in place,
 * and its comment threads in a rail beside the page. Tracked changes are accepted or rejected from the bar above the page. */
export function DocxViewerPanel({
  threadId,
  path,
  refreshKey,
}: {
  threadId: string;
  path: string;
  refreshKey: string;
}) {
  const dock = useDockPanel();
  const [view, setView] = useState<DocxView>("review");
  const [review, setReview] = useState<DocxReview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [anchors, setAnchors] = useState<Anchor[]>([]);
  const [matched, setMatched] = useState(true);
  const [active, setActive] = useState<string | null>(null);
  const [cardTops, setCardTops] = useState<Record<string, number>>({});
  const [step, setStep] = useState(-1);
  const [zoom, setZoom] = useState(1);
  const [compact, setCompact] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef(new Map<string, HTMLElement>());
  const railRef = useRef<HTMLDivElement>(null);
  const { busy, reloads, keepScroll, act } = useDocxActions(threadId, path, scrollerRef, setError);
  const { pick, selectedChange } = useChangeSelection(pageRef, review, matched);
  const name = path.split(/[\\/]/).pop() ?? path;

  const measure = useCallback(() => {
    const page = pageRef.current;
    const content = contentRef.current;
    if (!page || !content) return;
    const box = content.getBoundingClientRect();
    const found: Anchor[] = [];
    for (const [id, range] of commentRanges(page)) {
      const rects = [...range.getClientRects()].filter((r) => r.width > 0);
      const first = rects[0] ?? range.getBoundingClientRect();
      const line = rects.filter((r) => Math.abs(r.top - first.top) < 2);
      const right = Math.max(...line.map((r) => r.right), first.right);
      found.push({ id, range, top: first.top - box.top, right: right - box.left });
    }
    setAnchors(found.sort((a, b) => a.top - b.top));
  }, []);

  // Pages keep their printed width, scaled down to fit beside the rail.
  const fit = useCallback(() => {
    const scroller = scrollerRef.current;
    const section = pageRef.current?.querySelector<HTMLElement>("section.docx");
    if (!scroller || !section) return;
    const besideRail = (scroller.clientWidth - RAIL_WIDTH - 3 * 16) / section.offsetWidth;
    const narrow = besideRail < MIN_ZOOM_BESIDE_RAIL;
    setCompact(narrow);
    const alone = (scroller.clientWidth - 2 * 16) / section.offsetWidth;
    setZoom(Math.max(0.3, Math.min(1, narrow ? alone : besideRail)));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    Promise.all([getDocxReview(threadId, path), getDocxBytes(threadId, path, view), import("docx-preview")])
      .then(async ([nextReview, bytes, docx]) => {
        const page = pageRef.current;
        if (cancelled || !page) return;
        await docx.renderAsync(bytes, page, undefined, {
          className: "docx",
          inWrapper: true,
          renderChanges: view === "review",
          renderComments: true,
          experimental: true,
        });
        if (cancelled) return;
        setReview(nextReview);
        const marks = page.querySelectorAll("ins, del").length;
        const expected = view === "review" ? nextReview.changes.length : 0;
        setMatched(marks === expected && commentRanges(page).size >= nextReview.comments.length);
        fit();
        measure();
        if (keepScroll.current !== null) scrollerRef.current?.scrollTo({ top: keepScroll.current });
        keepScroll.current = null;
      })
      .catch((e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      cancelled = true;
    };
  }, [threadId, path, view, refreshKey, reloads, keepScroll, fit, measure]);

  useEffect(() => {
    const scroller = scrollerRef.current;
    const page = pageRef.current;
    if (!scroller || !page) return;
    const observer = new ResizeObserver(() => {
      fit();
      measure();
    });
    observer.observe(scroller);
    observer.observe(page);
    return () => observer.disconnect();
  }, [fit, measure]);

  const threads = (review?.comments ?? []).filter((c) => anchors.some((a) => a.id === c.id));
  const unanchored = (review?.comments ?? []).filter((c) => !anchors.some((a) => a.id === c.id));
  const ordered = [...threads].sort(
    (a, b) => (anchors.find((x) => x.id === a.id)?.top ?? 0) - (anchors.find((x) => x.id === b.id)?.top ?? 0),
  );

  useLayoutEffect(() => {
    const tops = stackCards(
      ordered.map((c) => ({
        id: c.id,
        anchor: anchors.find((a) => a.id === c.id)!.top,
        height: cardRefs.current.get(c.id)?.offsetHeight ?? 64,
      })),
      active,
      CARD_GAP,
    );
    setCardTops((prev) => (JSON.stringify(prev) === JSON.stringify(tops) ? prev : tops));
  });

  useEffect(() => {
    const highlights = (CSS as unknown as { highlights?: Map<string, unknown> }).highlights;
    const anchor = anchors.find((a) => a.id === active);
    if (!highlights || typeof Highlight === "undefined") return;
    if (anchor) highlights.set("docx-active", new Highlight(anchor.range));
    else highlights.delete("docx-active");
  }, [active, anchors]);

  // Previous and next walk the changes and the comments in page order.
  const go = (delta: number) => {
    const list = stops(contentRef.current, pageRef.current, anchors);
    if (list.length === 0) return;
    const next = (step + delta + list.length) % list.length;
    setStep(next);
    const stop = list[next];
    setActive(stop.comment ?? null);
    pick(stop.el);
    contentRef.current?.parentElement?.scrollTo({
      top: Math.max(0, stop.top - 120),
      behavior: "smooth",
    });
    if (stop.el) {
      stop.el.classList.remove("docx-flash");
      void (stop.el as HTMLElement).offsetWidth;
      stop.el.classList.add("docx-flash");
    }
  };

  const changeCount = view === "review" ? (review?.changes.length ?? 0) : 0;
  const commentCount = review?.comments.length ?? 0;
  const iconButton =
    "flex h-7 w-7 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)] disabled:opacity-40";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-12 shrink-0 items-center gap-2 px-3" {...dock.headerProps}>
        <span className="min-w-0 flex-1 truncate px-1 text-[15px]" title={path}>
          {name}
        </span>
        <button
          type="button"
          className={iconButton}
          title="Open in Word"
          aria-label="Open in Word"
          onClick={() => void openThreadFile(threadId, path, false).then((e) => e && setError(e))}
        >
          <ExternalLinkIcon className="h-4 w-4" />
        </button>
        {dock.controls}
      </div>
      <div className="flex h-10 shrink-0 items-center gap-2 border-y border-[var(--border)] px-3 text-xs text-[var(--muted)]">
        <ViewSwitch
          view={view}
          onPick={(next) => {
            setView(next);
            setStep(-1);
          }}
        />
        <span className="flex-1 truncate pl-1">
          {changeCount} {changeCount === 1 ? "change" : "changes"}
          {!compact && ` · ${commentCount} ${commentCount === 1 ? "comment" : "comments"}`}
          {review && review.other_changes > 0 && view === "review" && ` · ${review.other_changes} more in Word`}
        </span>
        {compact && commentCount > 0 && (
          <button
            type="button"
            aria-expanded={drawer}
            title={drawer ? "Hide comments" : "Show comments"}
            className={`flex h-7 shrink-0 items-center gap-1 rounded-md px-1.5 hover:bg-[var(--card-bg)] hover:text-[var(--fg)] ${drawer ? "bg-[var(--card-bg)] text-[var(--fg)]" : ""}`}
            onClick={() => setDrawer((open) => !open)}
          >
            <MessageCircleIcon className="h-3.5 w-3.5" />
            <span className="tabular-nums">{commentCount}</span>
          </button>
        )}
        <button type="button" className={iconButton} title="Previous" aria-label="Previous" onClick={() => go(-1)}>
          <ArrowUpIcon className="h-3.5 w-3.5" />
        </button>
        <button type="button" className={iconButton} title="Next" aria-label="Next" onClick={() => go(1)}>
          <ArrowDownIcon className="h-3.5 w-3.5" />
        </button>
      </div>
      {view === "review" && changeCount > 0 && (
        <DocxChangeBar selected={selectedChange} count={changeCount} busy={busy} onAct={act} />
      )}
      <DocxNewComment page={pageRef} busy={busy} onAct={act} />
      {error && <div className="px-4 py-2 text-xs text-[var(--danger)]">{error}</div>}
      <div className="relative flex min-h-0 flex-1 flex-col">
        {compact && drawer && (
          <div className="absolute inset-y-0 right-0 z-20 w-[min(300px,85%)] overflow-auto border-l border-[var(--border)] bg-[var(--panel-bg)] p-3 shadow-[var(--panel-shadow)]">
            {(review?.comments ?? []).map((comment) => (
              <DocxCommentCard
                key={comment.id}
                busy={busy}
                onAct={act}
                comment={comment}
                active={active === comment.id}
                onActivate={() => {
                  setActive(comment.id);
                  const anchor = anchors.find((a) => a.id === comment.id);
                  if (anchor) scrollerRef.current?.scrollTo({ top: Math.max(0, anchor.top - 120), behavior: "smooth" });
                }}
              />
            ))}
          </div>
        )}
        <div
          ref={scrollerRef}
          className="docx-viewer min-h-0 flex-1 overflow-auto bg-[var(--bg)]"
          onClick={(e) => {
            setActive(null);
            pick(e.target as Element);
          }}
        >
          <div ref={contentRef} className="relative mx-auto flex w-max gap-4 p-4">
            <div ref={pageRef} className="docx-page" style={{ zoom }} />
            <div ref={railRef} className={`relative shrink-0 ${compact ? "hidden" : ""}`} style={{ width: RAIL_WIDTH }}>
              {ordered.map((comment) => (
                <DocxCommentCard
                  key={comment.id}
                  busy={busy}
                  onAct={act}
                  comment={comment}
                  top={cardTops[comment.id] ?? 0}
                  active={active === comment.id}
                  onActivate={() => setActive(comment.id)}
                  cardRef={(el) => {
                    if (el) cardRefs.current.set(comment.id, el);
                    else cardRefs.current.delete(comment.id);
                  }}
                />
              ))}
              {unanchored.length > 0 && (
                <div className="absolute inset-x-0" style={{ top: Math.max(0, ...Object.values(cardTops)) + 96 }}>
                  {unanchored.map((comment) => (
                    <DocxCommentCard key={comment.id} comment={comment} active={false} busy={busy} onAct={act} onActivate={() => {}} />
                  ))}
                </div>
              )}
            </div>
            {matched && !compact && (
              <svg className="pointer-events-none absolute inset-0 h-full w-full overflow-visible" aria-hidden>
                {ordered.map((comment) => {
                  const anchor = anchors.find((a) => a.id === comment.id)!;
                  const railLeft = railRef.current?.offsetLeft ?? 0;
                  const y1 = anchor.top + 8;
                  const pageEdge = railLeft - 16;
                  const y2 = (cardTops[comment.id] ?? anchor.top) + 14;
                  return (
                    <path
                      key={comment.id}
                      d={`M ${anchor.right + 2} ${y1} L ${pageEdge} ${y1} C ${pageEdge + 10} ${y1}, ${railLeft - 10} ${y2}, ${railLeft} ${y2}`}
                      fill="none"
                      stroke={active === comment.id ? "var(--accent)" : "var(--border-hover)"}
                      strokeWidth={active === comment.id ? 1.5 : 1}
                    />
                  );
                })}
              </svg>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
