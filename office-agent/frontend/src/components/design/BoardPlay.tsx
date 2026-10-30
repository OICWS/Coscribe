import { useEffect, useRef, useState } from "react";
import { designFileUrl } from "../../lib/artifacts";
import type { CanvasBoard } from "../../lib/designCanvas";
import { PlayIcon } from "../icons";
import type { Scheme } from "./useCanvasLook";
import type { PlayMode } from "./useBoardPlay";

/** Above a board: Play, which asks where (on the canvas or filling the panel), or Edit while the
 * board is played on the canvas. */
export function BoardPlayButton({ live, onPlay, onEdit }: { live: boolean; onPlay: (mode: PlayMode) => void; onEdit: () => void }) {
  const [open, setOpen] = useState(false);
  const pill = "flex h-5 items-center gap-1 rounded-md border px-1.5 text-[11px] font-medium uppercase tracking-wide";
  if (live) {
    return (
      <button type="button" className={`${pill} border-[var(--text)] bg-[var(--text)] text-[var(--bg)]`} onPointerDown={(e) => e.stopPropagation()} onClick={onEdit}>
        Edit
      </button>
    );
  }
  return (
    <div className="relative" onPointerDown={(e) => e.stopPropagation()}>
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        className={`${pill} border-[var(--border)] text-[var(--muted)] hover:text-[var(--text)]`}
        onClick={() => setOpen((o) => !o)}
      >
        <PlayIcon className="h-3 w-3" />
        Play
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-full z-20 mt-1 w-40 rounded-lg border border-[var(--border)] bg-[var(--panel-bg)] p-1 normal-case shadow-[var(--shadow)]">
          {(
            [
              ["canvas", "Play on canvas"],
              ["full", "Play full screen"],
            ] as const
          ).map(([mode, label]) => (
            <button
              key={mode}
              type="button"
              role="menuitem"
              className="block w-full rounded-md px-2 py-1.5 text-left text-[13px] hover:bg-[var(--card-bg)]"
              onClick={() => {
                setOpen(false);
                onPlay(mode);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** One board filling the panel, fitted and centred at no more than its real size; Edit or Escape
 * goes back to the canvas. */
export function FullScreenPlayer({ board, threadId, version, scheme, onClose }: { board: CanvasBoard; threadId: string; version: string; scheme: Scheme; onClose: () => void }) {
  const area = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const el = area.current;
    if (!el) return;
    const measure = () => setScale(Math.min(1, (el.clientWidth - 32) / board.width, (el.clientHeight - 32) / board.height));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [board.width, board.height]);
  return (
    <div className="absolute inset-0 z-30 flex flex-col bg-[var(--card-bg)]" data-testid="board-full-screen">
      <div className="flex h-11 shrink-0 items-center gap-2 px-3">
        <span className="min-w-0 flex-1 truncate text-sm text-[var(--muted)]">{board.title}</span>
        <button type="button" className="h-7 rounded-md border border-[var(--border)] bg-[var(--panel-bg)] px-2.5 text-xs font-medium hover:bg-[var(--card-bg)]" onClick={onClose}>
          Edit
        </button>
      </div>
      <div ref={area} className="relative min-h-0 flex-1 overflow-hidden">
        <iframe
          key={`${board.path}.${version}.${scheme}`}
          title={board.title}
          data-board={board.id}
          src={designFileUrl(threadId, board.path, version, scheme)}
          sandbox="allow-scripts"
          className="absolute left-1/2 top-1/2 border-0 bg-white shadow-sm"
          style={{ width: board.width, height: board.height, transform: `translate(-50%, -50%) scale(${scale})` }}
        />
      </div>
    </div>
  );
}
