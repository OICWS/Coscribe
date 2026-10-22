import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { CheckIcon, ChevronRightIcon } from "../icons";

interface MenuItem {
  label: string;
  /** Right-aligned, muted: a shortcut. */
  hint?: string;
  icon?: ReactNode;
  disabled?: boolean;
  checked?: boolean;
  /** Drawn red: removes something. */
  danger?: boolean;
  /** A lower-case key that picks it while the menu is open. */
  accel?: string;
  onSelect?: () => void;
  /** A second line under the label, muted. */
  description?: string;
  /** Drawn at the right end of the row (a download arrow, say). */
  trailing?: ReactNode;
  /** The row opens a second menu to its right instead of doing something. */
  submenu?: MenuEntry[];
}

/** A divider, or a muted line of text that is not an item. */
export type MenuEntry = MenuItem | "divider" | { note: string };

/** A menu under `anchor`, aligned to its right edge (or `align` left); closes on a pick, Escape
 * or a click outside. */
export function SlideMenu({
  anchor,
  entries,
  label,
  width = 200,
  align = "right",
  onClose,
}: {
  anchor: DOMRect;
  entries: MenuEntry[];
  label: string;
  width?: number;
  align?: "left" | "right";
  onClose: () => void;
}) {
  const menuRef = useRef<HTMLDivElement>(null);
  const flyoutRef = useRef<HTMLDivElement>(null);
  // The open submenu: its entries, and where its row is.
  const [flyout, setFlyout] = useState<{ entries: MenuEntry[]; row: DOMRect } | null>(null);
  // Under the anchor, or higher up when a long menu would run off the window.
  const [top, setTop] = useState(anchor.bottom + 6);
  useLayoutEffect(() => {
    const height = menuRef.current?.offsetHeight ?? 0;
    setTop(Math.max(8, Math.min(anchor.bottom + 6, window.innerHeight - height - 8)));
  }, [anchor, entries.length]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      const bare = !(e.ctrlKey || e.metaKey || e.altKey);
      const hit = entries.find((entry): entry is MenuItem => typeof entry === "object" && "label" in entry && bare && entry.accel === e.key.toLowerCase() && !entry.disabled);
      if (hit) {
        onClose();
        hit.onSelect?.();
      }
    };
    const onDown = (e: PointerEvent) => {
      const target = e.target as Node;
      if (!menuRef.current?.contains(target) && !flyoutRef.current?.contains(target)) onClose();
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onDown, true);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onDown, true);
    };
  }, [entries, onClose]);

  const rows = (list: MenuEntry[], inFlyout: boolean) =>
    list.map((entry, i) => (
      <MenuRow
        key={i}
        entry={entry}
        open={typeof entry === "object" && "submenu" in entry && flyout?.entries === entry.submenu}
        onOpenSub={(sub, row) => (inFlyout ? undefined : setFlyout(sub ? { entries: sub, row } : null))}
        onClose={onClose}
      />
    ));

  const menuLeft = Math.max(8, Math.min(window.innerWidth - width - 8, align === "left" ? anchor.left : anchor.right - width));
  const flyoutWidth = 288;
  // Beside the menu on its right, or on its left when the window has no room there.
  const flyoutLeft = menuLeft + width + 6 + flyoutWidth <= window.innerWidth - 8 ? menuLeft + width + 6 : Math.max(8, menuLeft - flyoutWidth - 6);

  return createPortal(
    <>
      <div
        ref={menuRef}
        role="menu"
        aria-label={label}
        className="fixed z-50 overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--bg)] p-1.5 shadow-[0_8px_28px_rgba(0,0,0,0.12)]"
        style={{ top, maxHeight: window.innerHeight - 16, left: menuLeft, width }}
      >
        {rows(entries, false)}
      </div>
      {flyout && (
        <div
          ref={flyoutRef}
          role="menu"
          aria-label={`${label}, more`}
          className="fixed z-50 overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--bg)] p-1.5 shadow-[0_8px_28px_rgba(0,0,0,0.12)]"
          style={{ top: Math.max(8, Math.min(flyout.row.top - 6, window.innerHeight - 8 - 72 * flyout.entries.length)), maxHeight: window.innerHeight - 16, left: flyoutLeft, width: flyoutWidth }}
        >
          {rows(flyout.entries, true)}
        </div>
      )}
    </>,
    document.body,
  );
}

/** One row of a menu: a divider, a note, or an item that acts or opens a second menu. */
function MenuRow({
  entry,
  open,
  onOpenSub,
  onClose,
}: {
  entry: MenuEntry;
  open: boolean;
  /** The pointer reached a row (its submenu, or none), or the row was clicked. */
  onOpenSub: (submenu: MenuEntry[] | undefined, row: DOMRect) => void;
  onClose: () => void;
}) {
  if (entry === "divider") return <div className="mx-1.5 my-1.5 border-t border-[var(--border)]" />;
  if ("note" in entry) return <div className="px-2.5 py-1 text-[13px] text-[var(--muted)]">{entry.note}</div>;
  const opens = entry.submenu !== undefined;
  return (
    <button
      type="button"
      role={entry.checked === undefined ? "menuitem" : "menuitemradio"}
      aria-checked={entry.checked}
      aria-haspopup={opens ? "menu" : undefined}
      aria-expanded={opens ? open : undefined}
      disabled={entry.disabled}
      className={`flex w-full items-center gap-2 rounded-lg px-2.5 text-left text-sm hover:bg-[var(--card-bg)] disabled:text-[var(--muted)] disabled:opacity-60 disabled:hover:bg-transparent ${entry.description ? "min-h-12 py-1.5" : "h-8"} ${entry.danger ? "text-[var(--danger)]" : "text-[var(--fg)]"}`}
      onPointerEnter={(e) => onOpenSub(entry.submenu, e.currentTarget.getBoundingClientRect())}
      onClick={(e) => {
        if (entry.submenu) {
          onOpenSub(entry.submenu, e.currentTarget.getBoundingClientRect());
          return;
        }
        onClose();
        entry.onSelect?.();
      }}
    >
      {entry.icon}
      <span className="min-w-0 flex-1">
        <span className="block truncate">{entry.label}</span>
        {entry.description && <span className="block truncate text-xs text-[var(--muted)]">{entry.description}</span>}
      </span>
      {entry.hint && <span className="text-xs text-[var(--muted)]">{entry.hint}</span>}
      {entry.checked && <CheckIcon className="h-4 w-4 shrink-0" />}
      {entry.trailing}
      {opens && <ChevronRightIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />}
    </button>
  );
}
