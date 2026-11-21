import { createPortal } from "react-dom";

export interface ModelTipAnchor {
  rect: DOMRect;
  lines: string[];
  /** Where it goes when there is room: a submenu opening to the left keeps its tips there too. */
  side?: "left" | "right";
}

const WIDTH = 280;
const GAP = 8;

/** The dark tip beside a hovered model: fixed to the viewport, so a menu's or a list's own
 * scrolling can't clip it; on the other side when the preferred one has no room. */
export function ModelTip({ tip }: { tip: ModelTipAnchor | null }) {
  if (!tip || tip.lines.length === 0) return null;
  const { rect, lines } = tip;
  const roomRight = rect.right + GAP + WIDTH <= window.innerWidth;
  const roomLeft = rect.left - GAP - WIDTH >= 0;
  const onLeft = tip.side === "left" ? roomLeft || !roomRight : !roomRight;
  const style = {
    top: rect.top + rect.height / 2,
    maxWidth: WIDTH,
    ...(onLeft ? { right: window.innerWidth - rect.left + GAP } : { left: rect.right + GAP }),
  };
  return createPortal(
    <div
      role="tooltip"
      className="pointer-events-none fixed z-[1000] -translate-y-1/2 rounded-lg bg-[var(--fg)] px-3 py-2 text-[13px] leading-snug text-[var(--bg)] shadow-[var(--shadow)]"
      style={style}
    >
      {lines.map((line) => (
        <div key={line}>{line}</div>
      ))}
    </div>,
    document.body,
  );
}
