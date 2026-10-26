import { useSyncExternalStore } from "react";

/** The narrowest the conversation can be before the composer's toolbar no longer fits on one
 * row. The composer measures it (it depends on the font, the pickers' labels and whether the
 * time and token count show); the dock reads it to stop squeezing the conversation there. */
/** Room for a font that loads after the first measure and for subpixel rounding. */
const SLACK = 8;
/** Room kept for the running time and token count ("12m 34s · 128.5k tokens"), which only show
 * while a turn runs: a turn that starts with the conversation already at its narrowest must
 * not overflow the toolbar. */
const STATUS_RESERVE = 150;
let needed = 0;
const listeners = new Set<() => void>();

function setComposerNeededWidth(width: number): void {
  const next = Math.ceil(width) + SLACK;
  if (next === needed) return;
  needed = next;
  listeners.forEach((listener) => listener());
}

/** Ref for the composer's toolbar. Its items never shrink, so its width is the sum of theirs
 * plus the gaps; the composer's own padding comes on top. */
export function measureComposerToolbar(bar: HTMLDivElement | null): (() => void) | undefined {
  const root = bar?.parentElement;
  if (!bar || !root) return undefined;
  const measure = () => {
    const gap = parseFloat(getComputedStyle(bar).columnGap) || 0;
    const items = Array.from(bar.children) as HTMLElement[];
    const status = bar.querySelector<HTMLElement>('[data-testid="run-status"]');
    const slots = items.length + (status ? 0 : 1);
    const content =
      items.reduce((sum, el) => sum + el.offsetWidth, 0) +
      Math.max(0, STATUS_RESERVE - (status?.offsetWidth ?? 0)) +
      gap * Math.max(0, slots - 1);
    setComposerNeededWidth(content + (root.getBoundingClientRect().width - bar.clientWidth));
  };
  const observer = new ResizeObserver(measure);
  observer.observe(root);
  Array.from(bar.children).forEach((el) => observer.observe(el));
  measure();
  return () => observer.disconnect();
}

export function useComposerNeededWidth(floor: number, ceiling: number): number {
  const width = useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => needed,
  );
  return Math.min(ceiling, Math.max(floor, width));
}
