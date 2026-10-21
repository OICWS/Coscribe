import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { slashExtension, type SlashItem, type SlashOpen } from "../../lib/docsSlash";

/** The menu "/" opens: lines to arrow through, Enter to pick, Escape to close (the editor handles that one). */
export function useSlashMenu() {
  const [open, setOpen] = useState<SlashOpen | null>(null);
  const [selected, setSelected] = useState(0);
  const live = useRef({ open, selected });
  useEffect(() => {
    live.current = { open, selected };
  }, [open, selected]);

  const extension = useMemo(
    () =>
      slashExtension({
        show: (next) => {
          setOpen(next);
          setSelected(0);
        },
        key: (event) => {
          const { open: now, selected: at } = live.current;
          if (!now || now.items.length === 0) return false;
          const move = (delta: number) => setSelected((at + delta + now.items.length) % now.items.length);
          if (event.key === "ArrowDown") move(1);
          else if (event.key === "ArrowUp") move(-1);
          else if (event.key === "Enter" || event.key === "Tab") now.choose(now.items[at]);
          else return false;
          return true;
        },
      }),
    [],
  );
  return { open, selected, setSelected, extension };
}

const WIDTH = 260;

export function SlashMenu({ open, selected, onHover }: { open: SlashOpen; selected: number; onHover: (index: number) => void }) {
  const list = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(0);
  useEffect(() => {
    setHeight(list.current?.offsetHeight ?? 0);
    list.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" });
  }, [open.items, selected]);
  if (open.items.length === 0 || !open.rect) return null;
  const below = open.rect.bottom + 6;
  const top = below + height > window.innerHeight - 8 ? Math.max(8, open.rect.top - 6 - height) : below;
  const left = Math.max(8, Math.min(window.innerWidth - WIDTH - 8, open.rect.left));
  return createPortal(
    <div
      ref={list}
      role="listbox"
      aria-label="Insert"
      className="fixed z-50 max-h-[380px] overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--bg)] p-1.5 shadow-[0_8px_28px_rgba(0,0,0,0.12)]"
      style={{ top, left, width: WIDTH }}
      onMouseDown={(e) => e.preventDefault()}
    >
      {open.items.map((item: SlashItem, index) => (
        <button
          key={item.id}
          type="button"
          role="option"
          aria-selected={index === selected}
          className={`flex w-full flex-col rounded-lg px-2.5 py-1.5 text-left ${index === selected ? "bg-[var(--card-bg)]" : ""}`}
          onMouseEnter={() => onHover(index)}
          onClick={() => open.choose(item)}
        >
          <span className="text-sm text-[var(--fg)]">{item.label}</span>
          <span className="text-xs text-[var(--muted)]">{item.hint}</span>
        </button>
      ))}
    </div>,
    document.body,
  );
}
