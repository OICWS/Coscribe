import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import { useClickOutside } from "../lib/useClickOutside";
import type { StateEvent } from "../types/wire";
import { UltraField } from "./UltraField";

export type Effort = StateEvent["effort"];

const EFFORTS: readonly Effort[] = ["low", "medium", "high", "extra", "max", "ultra"];
const RECOMMENDED: Effort = "medium";
const LABELS: Record<Effort, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  extra: "Extra",
  max: "Max",
  ultra: "Ultra",
};
interface EffortPickerProps {
  effort: Effort;
  /** The model's level the choice runs as; null when the model takes no effort setting. */
  runsAs: string | null;
  onChange: (effort: Effort) => void;
}

export function EffortPicker({ effort: confirmed, runsAs, onChange }: EffortPickerProps) {
  const [open, setOpen] = useState(false);
  // The level just picked, shown until the server confirms that same level: a key press or drag
  // step before then counts from it, and the replies to earlier steps must not pull it back.
  const [pending, setPending] = useState<Effort | null>(null);
  useEffect(() => {
    if (confirmed === pending) setPending(null);
  }, [confirmed, pending]);
  useEffect(() => {
    if (pending === null) return;
    // An error reply carries no state; do not keep showing a level that never took.
    const timer = window.setTimeout(() => setPending(null), 3000);
    return () => window.clearTimeout(timer);
  }, [pending]);
  const effort = pending ?? confirmed;
  const rootRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  useClickOutside(rootRef, () => setOpen(false), open);

  const unsupported = runsAs === null;
  const index = EFFORTS.indexOf(effort);
  const ultra = effort === "ultra";
  const note = unsupported ? "This model has no effort setting." : null;

  const pick = (next: Effort) => {
    if (next === effort) return;
    setPending(next);
    onChange(next);
  };
  const levelAt = (clientX: number): Effort => {
    const box = trackRef.current?.getBoundingClientRect();
    if (!box || box.width === 0) return effort;
    const share = Math.min(1, Math.max(0, (clientX - box.left) / box.width));
    return EFFORTS[Math.round(share * (EFFORTS.length - 1))];
  };
  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (unsupported) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    pick(levelAt(event.clientX));
  };
  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (unsupported || !event.currentTarget.hasPointerCapture(event.pointerId)) return;
    pick(levelAt(event.clientX));
  };
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = { ArrowLeft: -1, ArrowDown: -1, ArrowRight: 1, ArrowUp: 1 }[event.key];
    if (step === undefined || unsupported) return;
    event.preventDefault();
    pick(EFFORTS[Math.min(EFFORTS.length - 1, Math.max(0, index + step))]);
  };

  // Stops sit between the track's two 10px ends, so the thumb never overhangs the track.
  const at = (i: number) => `calc(10px + (100% - 20px) * ${i / (EFFORTS.length - 1)})`;

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        data-testid="effort-pill"
        title="How hard the model thinks"
        className={`flex h-8 items-center rounded-lg px-2 text-sm hover:bg-[var(--card-bg)] ${
          unsupported ? "text-[var(--muted)] opacity-60" : "text-[var(--muted)] hover:text-[var(--fg)]"
        }`}
        onClick={() => setOpen((v) => !v)}
      >
        <span className={ultra && !unsupported ? "effort-ultra-text font-medium" : ""}>{LABELS[effort]}</span>
      </button>
      {open && (
        <div
          data-testid="effort-panel"
          className="absolute bottom-full right-0 z-20 mb-1 w-72 rounded-[14px] border border-[var(--border)] bg-[var(--panel-bg)] px-4 pb-3 pt-3 shadow-[var(--shadow)]"
        >
          <div className="mb-3 flex items-center justify-between">
            <div className="text-[15px]">
              <span className="text-[var(--muted)]">Effort</span>{" "}
              <span className={ultra ? "effort-ultra-text font-medium" : "font-medium"}>{LABELS[effort]}</span>
            </div>
            <span
              className="flex h-5 w-5 cursor-help items-center justify-center rounded-full border border-[var(--border-hover)] text-[11px] text-[var(--muted)]"
              title="More effort lets the model reason longer: better on hard tasks, slower, and it costs more. Each model runs the nearest level it supports."
            >
              ?
            </span>
          </div>
          <div className="mb-1.5 flex justify-between text-[13px] text-[var(--muted)]">
            <span>Faster</span>
            <span>Smarter</span>
          </div>
          <div
            ref={trackRef}
            role="slider"
            tabIndex={unsupported ? -1 : 0}
            aria-label="Effort"
            aria-valuemin={0}
            aria-valuemax={EFFORTS.length - 1}
            aria-valuenow={index}
            aria-valuetext={LABELS[effort]}
            aria-disabled={unsupported}
            data-testid="effort-track"
            className={`relative h-8 select-none rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus)] ${
              unsupported ? "cursor-not-allowed opacity-50" : "cursor-pointer"
            } bg-[var(--card-bg)]`}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onKeyDown={onKeyDown}
          >
            {!ultra && (
              <div
                className="absolute inset-y-0 left-0 rounded-lg bg-[color-mix(in_srgb,var(--fg)_14%,transparent)]"
                style={{ width: `calc(20px + (100% - 20px) * ${index / (EFFORTS.length - 1)})` }}
              />
            )}
            {ultra && <UltraField />}
            {EFFORTS.map((level, i) =>
              i === index ? null : (
                <span
                  key={level}
                  className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full ${
                    level === RECOMMENDED ? "h-3 w-[3px]" : "h-1 w-1"
                  } bg-[var(--muted)] opacity-60`}
                  style={{ left: at(i) }}
                />
              ),
            )}
            <span
              data-testid="effort-thumb"
              className="absolute top-1/2 h-7 w-5 -translate-x-1/2 -translate-y-1/2 rounded-md border border-[var(--border)] bg-white shadow-sm transition-[left] duration-150"
              style={{ left: at(index) }}
            />
          </div>
          <div className="relative mt-1 h-5 text-[12px] text-[var(--muted)]">
            <span
              className="absolute -translate-x-1/4 whitespace-nowrap"
              style={{ left: at(EFFORTS.indexOf(RECOMMENDED)) }}
            >
              Recommended
            </span>
          </div>
          {note && <div className="mt-1 text-[12px] text-[var(--muted)]">{note}</div>}
        </div>
      )}
    </div>
  );
}
