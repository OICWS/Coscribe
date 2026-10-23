import { useEffect, useRef, useState, type ComponentType, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { TOOLBAR_ITEMS, type ToolbarItem } from "../../lib/toolbarItems";
import { DRAWS_TITLE_BAR, TITLE_BAR_ICON } from "../../lib/titleBar";
import { useClickOutside } from "../../lib/useClickOutside";
import { CheckIcon, ChevronDownIcon, PencilIcon } from "../icons";

/** One thing the bar can hold: a button when pinned, a row of the menu when not. */
export interface ToolbarEntry {
  id: ToolbarItem;
  /** The name in the edit list. */
  label: string;
  /** The menu row, when it says what pressing does (Show or Hide); else the label. */
  menuLabel?: string;
  /** The button's own tooltip, when it says more than the label (its state, a count). */
  title?: string;
  Icon: ComponentType<{ className?: string; strokeWidth?: number }>;
  active: boolean;
  onSelect: () => void;
  /** A count or mark over the button's corner. */
  badge?: ReactNode;
}

/** The down arrow at the end of the bar: what is not pinned, and Edit toolbar. */
export function ToolbarMenu({ entries, onEdit }: { entries: ToolbarEntry[]; onEdit: () => void }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  useClickOutside(rootRef, () => setOpen(false), open);
  const icon = DRAWS_TITLE_BAR ? TITLE_BAR_ICON : { className: "h-[18px] w-[18px]" };
  const row = "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm hover:bg-[var(--card-bg)]";
  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        title="More"
        aria-label="More"
        aria-haspopup="menu"
        aria-expanded={open}
        className={`flex h-8 w-6 shrink-0 items-center justify-center rounded-md ${
          DRAWS_TITLE_BAR ? "text-[var(--fg)]" : "text-[var(--muted)] hover:text-[var(--fg)]"
        } hover:bg-[var(--card-bg)]`}
        onClick={() => setOpen((v) => !v)}
      >
        <ChevronDownIcon {...icon} />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-full z-40 mt-1 w-56 rounded-[10px] border border-[var(--border)] bg-[var(--panel-bg)] p-1 shadow-[var(--shadow)]">
          {entries.map(({ id, label, menuLabel, Icon, active, onSelect, badge }) => (
            <button
              key={id}
              type="button"
              role="menuitem"
              className={`${row} ${active ? "font-medium" : ""}`}
              onClick={() => {
                setOpen(false);
                onSelect();
              }}
            >
              <Icon className="h-[18px] w-[18px] shrink-0 text-[var(--muted)]" />
              <span className="min-w-0 flex-1 truncate">{menuLabel ?? label}</span>
              {badge}
            </button>
          ))}
          {entries.length > 0 && <div className="my-1 border-t border-[var(--border)]" />}
          <button
            type="button"
            role="menuitem"
            className={row}
            onClick={() => {
              setOpen(false);
              onEdit();
            }}
          >
            <PencilIcon className="h-[18px] w-[18px] shrink-0 text-[var(--muted)]" />
            Edit toolbar
          </button>
        </div>
      )}
    </div>
  );
}

/** Which items stay on the bar. */
export function ToolbarDialog({
  entries,
  pinned,
  onChange,
  onClose,
}: {
  entries: ToolbarEntry[];
  pinned: readonly ToolbarItem[];
  onChange: (pinned: ToolbarItem[]) => void;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);
  const toggle = (id: ToolbarItem) => onChange(TOOLBAR_ITEMS.filter((item) => (item === id ? !pinned.includes(id) : pinned.includes(item))));
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        role="dialog"
        aria-label="Edit toolbar"
        className="w-[min(420px,100vw-2rem)] rounded-[14px] border border-[var(--border)] bg-[var(--panel-bg)] p-5 shadow-[var(--shadow)]"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-medium">Edit toolbar</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">Choose which items appear in your toolbar. The rest are in the menu beside it.</p>
        <ul className="mt-4 flex flex-col gap-3">
          {entries.map(({ id, label, Icon }) => {
            const on = pinned.includes(id);
            return (
              <li key={id}>
                <button type="button" role="checkbox" aria-checked={on} aria-label={label} className="flex w-full items-center gap-3 text-left text-sm" onClick={() => toggle(id)}>
                  <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border ${on ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--accent-fg)]" : "border-[var(--border)]"}`}>
                    {on && <CheckIcon className="h-3.5 w-3.5" />}
                  </span>
                  <Icon className="h-[18px] w-[18px] shrink-0 text-[var(--muted)]" />
                  {label}
                </button>
              </li>
            );
          })}
        </ul>
        <div className="mt-5 flex justify-end">
          <button type="button" className="rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-fg)]" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
