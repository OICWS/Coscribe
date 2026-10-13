import { useRef, useState } from "react";
import { MoreIcon } from "../../icons";
import { useClickOutside } from "../../../lib/useClickOutside";

export function ConnectorMenu({
  pinned,
  onReconnect,
  onCheckUpdate,
}: {
  pinned: boolean;
  onReconnect: () => void;
  onCheckUpdate: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false), open);
  const item = "flex w-full px-3 py-1.5 text-left text-sm hover:bg-[var(--card-bg)]";
  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-label="More connector actions"
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border)] text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
        onClick={() => setOpen((v) => !v)}
      >
        <MoreIcon className="h-4 w-4" />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-20 mt-1 min-w-44 rounded-[10px] border border-[var(--border)] bg-[var(--panel-bg)] py-1 shadow-[var(--shadow)]"
        >
          <button
            type="button"
            role="menuitem"
            className={item}
            onClick={() => {
              setOpen(false);
              onReconnect();
            }}
          >
            Reconnect
          </button>
          {pinned && (
            <button
              type="button"
              role="menuitem"
              className={item}
              onClick={() => {
                setOpen(false);
                onCheckUpdate();
              }}
            >
              Check for updates
            </button>
          )}
        </div>
      )}
    </div>
  );
}
