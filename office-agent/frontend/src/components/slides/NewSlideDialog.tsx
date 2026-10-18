import { useEffect, useLayoutEffect, useRef } from "react";
import { createPortal } from "react-dom";
import type { SlideLayout } from "../../lib/slideLayouts";
import { parseSection } from "../../lib/slideSource";
import { CloseIcon } from "../icons";
import { drawSection } from "./sectionDom";

const PREVIEW_WIDTH = 268;

/** New slide: the ten layouts, each drawn in the deck's own look; a pick adds that slide after
 * the current one. */
export function NewSlideDialog({ layouts, onPick, onClose }: { layouts: SlideLayout[]; onPick: (layout: SlideLayout) => void; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 p-6" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-label="New slide" className="flex max-h-full w-[650px] max-w-full flex-col rounded-2xl bg-[var(--bg)] shadow-[0_12px_40px_rgba(0,0,0,0.2)]">
        <div className="flex items-center justify-between px-7 pb-4 pt-6">
          <h2 className="text-[26px] font-semibold text-[var(--fg)]">New slide</h2>
          <button type="button" aria-label="Close" className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border)] hover:bg-[var(--card-bg)]" onClick={onClose}>
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-4 overflow-auto px-7 pb-7">
          {layouts.map((layout) => (
            <button key={layout.name} type="button" className="text-left" onClick={() => onPick(layout)}>
              <LayoutPreview source={layout.source} />
              <span className="block pt-1.5 text-[15px] text-[var(--muted)]">{layout.name}</span>
            </button>
          ))}
        </div>
      </div>
    </div>,
    document.body,
  );
}

function LayoutPreview({ source }: { source: string }) {
  const hostRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    drawSection(host.shadowRoot ?? host.attachShadow({ mode: "open" }), parseSection(source), []);
  }, [source]);
  const scale = PREVIEW_WIDTH / 1920;
  return (
    <span className="block overflow-hidden rounded-lg border border-[var(--border)] hover:border-[var(--accent)]" style={{ width: PREVIEW_WIDTH, height: 1080 * scale }}>
      <span ref={hostRef} className="block origin-top-left" style={{ width: 1920, height: 1080, transform: `scale(${scale})` }} />
    </span>
  );
}
