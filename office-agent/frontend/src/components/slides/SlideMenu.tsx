import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { CheckIcon } from "../icons";

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
      if (!menuRef.current?.contains(e.target as Node)) onClose();
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onDown, true);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onDown, true);
    };
  }, [entries, onClose]);

  return createPortal(
    <div
      ref={menuRef}
      role="menu"
      aria-label={label}
      className="fixed z-50 rounded-xl border border-[var(--border)] bg-[var(--bg)] p-1.5 shadow-[0_8px_28px_rgba(0,0,0,0.12)]"
      style={{
        top: anchor.bottom + 6,
        left: Math.max(8, Math.min(window.innerWidth - width - 8, align === "left" ? anchor.left : anchor.right - width)),
        width,
      }}
    >
      {entries.map((entry, i) => {
        if (entry === "divider") return <div key={i} className="mx-1.5 my-1.5 border-t border-[var(--border)]" />;
        if ("note" in entry) {
          return (
            <div key={i} className="px-2.5 py-1 text-[13px] text-[var(--muted)]">
              {entry.note}
            </div>
          );
        }
        return (
          <button
            key={i}
            type="button"
            role={entry.checked === undefined ? "menuitem" : "menuitemradio"}
            aria-checked={entry.checked}
            disabled={entry.disabled}
            className={`flex h-8 w-full items-center gap-2 rounded-lg px-2.5 text-left text-sm hover:bg-[var(--card-bg)] disabled:text-[var(--muted)] disabled:opacity-60 disabled:hover:bg-transparent ${entry.danger ? "text-[var(--danger)]" : "text-[var(--fg)]"}`}
            onClick={() => {
              onClose();
              entry.onSelect?.();
            }}
          >
            {entry.icon}
            <span className="flex-1 truncate">{entry.label}</span>
            {entry.hint && <span className="text-xs text-[var(--muted)]">{entry.hint}</span>}
            {entry.checked && <CheckIcon className="h-4 w-4 shrink-0" />}
          </button>
        );
      })}
    </div>,
    document.body,
  );
}
