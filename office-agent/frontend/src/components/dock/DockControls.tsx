import { useEffect, useRef, useState, type ComponentType, type SVGProps } from "react";
import { createPortal } from "react-dom";
import type { Direction, Edge, PanelId } from "../../lib/dockLayout";
import {
  CloseIcon,
  ExpandIcon,
  LayoutBottomIcon,
  LayoutColumnsIcon,
  LayoutFillIcon,
  LayoutLeftIcon,
  LayoutRightIcon,
  LayoutRowsIcon,
  LayoutTopIcon,
  ShrinkIcon,
} from "../icons";

export interface DockActions {
  filled: PanelId | null;
  panelCount: number;
  edgeOf: (id: PanelId) => Edge | null;
  move: (id: PanelId, edge: Edge) => void;
  fill: (id: PanelId | null) => void;
  arrange: (dir: Direction) => void;
  close: (id: PanelId) => void;
  setMenuOpen: (id: PanelId, open: boolean) => void;
}

const MOVES: { edge: Edge; label: string; icon: ComponentType<SVGProps<SVGSVGElement>> }[] = [
  { edge: "left", label: "Move to the left", icon: LayoutLeftIcon },
  { edge: "right", label: "Move to the right", icon: LayoutRightIcon },
  { edge: "top", label: "Move to the top", icon: LayoutTopIcon },
  { edge: "bottom", label: "Move to the bottom", icon: LayoutBottomIcon },
];

const headerButton =
  "flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]";
const menuButton =
  "flex h-8 w-10 items-center justify-center rounded-lg text-[var(--fg)] hover:bg-[var(--card-bg)] disabled:opacity-35 disabled:hover:bg-transparent";
const menuButtonOn = "flex h-8 w-10 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-ink)]";

// Long enough to cross the gap from the button into the menu.
const CLOSE_DELAY_MS = 220;

/** Expand (click: fill the window; hover: Move and Fill and arrange) and close. */
export function DockControls({ id, title, actions }: { id: PanelId; title: string; actions: DockActions }) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [anchor, setAnchor] = useState<DOMRect | null>(null);
  // After a click the pointer is still on the button; the menu waits until it leaves.
  const [quiet, setQuiet] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const filled = actions.filled === id;
  const { setMenuOpen } = actions;

  const open = () => {
    clearTimeout(closeTimer.current);
    if (quiet || !buttonRef.current) return;
    setAnchor(buttonRef.current.getBoundingClientRect());
  };
  const closeSoon = () => {
    clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(() => setAnchor(null), CLOSE_DELAY_MS);
  };
  const closeNow = () => {
    clearTimeout(closeTimer.current);
    setAnchor(null);
  };

  useEffect(() => {
    setMenuOpen(id, anchor !== null);
  }, [anchor, id, setMenuOpen]);
  useEffect(() => () => setMenuOpen(id, false), [id, setMenuOpen]);
  useEffect(() => () => clearTimeout(closeTimer.current), []);
  useEffect(() => {
    if (!anchor) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeNow();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [anchor]);

  const here = actions.edgeOf(id);
  const run = (action: () => void) => {
    closeNow();
    action();
  };

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        aria-label={filled ? `Restore ${title}` : `Expand ${title}`}
        aria-haspopup="menu"
        aria-expanded={anchor !== null}
        className={headerButton}
        onPointerEnter={open}
        onPointerLeave={() => {
          setQuiet(false);
          closeSoon();
        }}
        onFocus={open}
        onClick={() => {
          closeNow();
          setQuiet(true);
          actions.fill(filled ? null : id);
        }}
      >
        {filled ? <ShrinkIcon className="h-4 w-4" /> : <ExpandIcon className="h-4 w-4" />}
      </button>
      <button type="button" title="Close" aria-label={`Close ${title}`} className={headerButton} onClick={() => actions.close(id)}>
        <CloseIcon className="h-4 w-4" />
      </button>
      {anchor &&
        createPortal(
          <div
            role="menu"
            aria-label={`Arrange ${title}`}
            className="fixed z-50 w-[232px] rounded-xl border border-[var(--border)] bg-[var(--bg)] p-2.5 shadow-[0_8px_28px_rgba(0,0,0,0.12)]"
            style={{
              top: anchor.bottom + 6,
              left: Math.max(8, Math.min(window.innerWidth - 240, anchor.right - 232)),
            }}
            onPointerEnter={() => clearTimeout(closeTimer.current)}
            onPointerLeave={closeSoon}
          >
            <div className="px-1 pb-1.5 text-[13px] text-[var(--muted)]">Move</div>
            <div className="mb-2.5 flex gap-1.5">
              {MOVES.map(({ edge, label, icon: Icon }) => (
                <button
                  key={edge}
                  type="button"
                  role="menuitem"
                  title={label}
                  aria-label={label}
                  className={here === edge ? menuButtonOn : menuButton}
                  disabled={actions.panelCount < 2}
                  onClick={() => run(() => actions.move(id, edge))}
                >
                  <Icon className="h-[18px] w-[18px]" />
                </button>
              ))}
            </div>
            <div className="px-1 pb-1.5 text-[13px] text-[var(--muted)]">Fill and arrange</div>
            <div className="flex gap-1.5">
              <button
                type="button"
                role="menuitem"
                title={filled ? "Restore" : "Fill the window"}
                aria-label={filled ? "Restore" : "Fill the window"}
                className={filled ? menuButtonOn : menuButton}
                onClick={() => run(() => actions.fill(filled ? null : id))}
              >
                <LayoutFillIcon className="h-[18px] w-[18px]" />
              </button>
              <button
                type="button"
                role="menuitem"
                title="Side by side"
                aria-label="Side by side"
                className={menuButton}
                disabled={actions.panelCount < 2}
                onClick={() => run(() => actions.arrange("row"))}
              >
                <LayoutColumnsIcon className="h-[18px] w-[18px]" />
              </button>
              <button
                type="button"
                role="menuitem"
                title="Stacked"
                aria-label="Stacked"
                className={menuButton}
                disabled={actions.panelCount < 2}
                onClick={() => run(() => actions.arrange("col"))}
              >
                <LayoutRowsIcon className="h-[18px] w-[18px]" />
              </button>
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
