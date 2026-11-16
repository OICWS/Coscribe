import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { formatTokenCount } from "../lib/format";
import { ContextBreakdownPanel } from "./ContextBreakdownPanel";

interface ContextRingProps {
  threadId: string;
  totalTokens: number;
  contextWindow: number;
  /** null when the provider hasn't reported prompt-cache stats yet this
   * session -- see reducer.ts's own comment on why that stays distinct
   * from "reported, zero tokens cached." */
  cacheStats: { cacheReadTokens: number; inputTokens: number; hitRate: number } | null;
}

const RADIUS = 9;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Viewport-bound usage details, independent of the conversation panel's clipping. */
export function ContextRing({ threadId, totalTokens, contextWindow, cacheStats }: ContextRingProps) {
  const [open, setOpen] = useState(false);
  // Bumped every time the popover opens -- ContextBreakdownPanel re-fetches
  // when this changes, so the breakdown reflects "as of the moment you
  // opened it" without polling while the popover stays closed.
  const [refreshKey, setRefreshKey] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ left: 8, top: 8 });
  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node) && !panelRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const key = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", key); };
  }, [open]);
  useLayoutEffect(() => {
    if (!open || !panelRef.current) return;
    const update = () => {
      const anchor = rootRef.current?.getBoundingClientRect();
      const panel = panelRef.current?.getBoundingClientRect();
      if (!anchor || !panel) return;
      const next = {
        left: Math.max(8, Math.min(anchor.right - panel.width, window.innerWidth - panel.width - 8)),
        top: Math.max(8, Math.min(anchor.top - panel.height - 6, window.innerHeight - panel.height - 8)),
      };
      setPosition(previous => previous.left === next.left && previous.top === next.top ? previous : next);
    };
    const observer = new ResizeObserver(update);
    observer.observe(panelRef.current);
    if (rootRef.current) observer.observe(rootRef.current);
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    update();
    return () => { observer.disconnect(); window.removeEventListener("resize", update); window.removeEventListener("scroll", update, true); };
  }, [open]);

  if (!contextWindow || totalTokens === 0) return null;
  const percent = Math.min(100, (totalTokens / contextWindow) * 100);
  const offset = CIRCUMFERENCE * (1 - percent / 100);

  return (
    // mr-2.5 puts the ring's centre under the Send button's, which sits inside
    // the input box above.
    <div className="relative mr-2.5 shrink-0" ref={rootRef}>
      <button
        type="button"
        title="Context window"
        className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
        onClick={() =>
          setOpen((v) => {
            if (!v) setRefreshKey((k) => k + 1);
            return !v;
          })
        }
      >
        <svg viewBox="0 0 24 24" className="h-5 w-5 -rotate-90">
          <circle cx="12" cy="12" r={RADIUS} fill="none" stroke="var(--border)" strokeWidth="3" />
          <circle
            cx="12"
            cy="12"
            r={RADIUS}
            fill="none"
            stroke="var(--accent)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
          />
        </svg>
      </button>
      {open && createPortal(
        <div ref={panelRef} data-native-overlay role="dialog" aria-label="Context usage" style={position} className="fixed z-[1000] max-h-[calc(100dvh-16px)] w-80 max-w-[calc(100vw-16px)] overflow-y-auto rounded-[10px] border border-[var(--border)] bg-[var(--panel-bg)] p-3 text-sm shadow-[var(--shadow)]">
          <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
            <span className="shrink-0 text-xs text-[var(--muted)]">Context window</span>
            <span className="ml-auto max-w-full text-right text-xs tabular-nums [overflow-wrap:anywhere]">
              {formatTokenCount(totalTokens)} / <span className="inline-block whitespace-nowrap">{formatTokenCount(contextWindow)} ({percent.toFixed(0)}%)</span>
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-[var(--border)]">
            <div className="h-full bg-[var(--accent)]" style={{ width: `${percent}%` }} />
          </div>
          {cacheStats && (
            <div className="mt-1.5 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 border-t border-[var(--border)] pt-1.5">
              <span className="shrink-0 text-xs text-[var(--muted)]" title="Last call">Cache hit</span>
              <span className="ml-auto max-w-full text-right text-xs tabular-nums [overflow-wrap:anywhere]">
                {formatTokenCount(cacheStats.cacheReadTokens)} / <span className="inline-block whitespace-nowrap">{formatTokenCount(cacheStats.inputTokens)} ({(cacheStats.hitRate * 100).toFixed(0)}%)</span>
              </span>
            </div>
          )}
          <ContextBreakdownPanel threadId={threadId} refreshKey={refreshKey} />
        </div>, document.body
      )}
    </div>
  );
}
