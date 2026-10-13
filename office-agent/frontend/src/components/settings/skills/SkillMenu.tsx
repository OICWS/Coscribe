import { useRef, useState } from "react";
import { useClickOutside } from "../../../lib/useClickOutside";
import type { SkillInfo } from "../../../types/settings";
import { MoreIcon } from "../../icons";

/** "Off"/"On" and, unless it ships with coscribe, Remove. */
export function SkillMenu({
  skill,
  onToggle,
  onRemove,
}: {
  skill: SkillInfo;
  onToggle: () => void;
  onRemove: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false), open);
  const item = "flex w-full px-3 py-1.5 text-left text-sm hover:bg-[var(--card-bg)]";
  return (
    <div className="relative" ref={ref} onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        aria-label={`Options for ${skill.name}`}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-8 w-8 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
        onClick={() => setOpen((v) => !v)}
      >
        <MoreIcon className="h-4 w-4" />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-20 mt-1 min-w-36 rounded-[10px] border border-[var(--border)] bg-[var(--panel-bg)] py-1 shadow-[var(--shadow)]"
        >
          <button
            type="button"
            role="menuitem"
            className={item}
            onClick={() => {
              setOpen(false);
              onToggle();
            }}
          >
            {skill.enabled ? "Turn off" : "Turn on"}
          </button>
          {skill.source !== "builtin" && (
            <button
              type="button"
              role="menuitem"
              className={`${item} text-[var(--danger)]`}
              onClick={() => {
                setOpen(false);
                onRemove();
              }}
            >
              Remove
            </button>
          )}
        </div>
      )}
    </div>
  );
}
