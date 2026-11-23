import { useRef, useState } from "react";
import { useClickOutside } from "../../../lib/useClickOutside";
import { ChevronDownIcon, PencilIcon, PlusIcon, UploadIcon } from "../../icons";

/** Settings > Plugins' Add: upload a plugin or a skill, or write a skill with coscribe. */
export function AddMenu({ onUpload, onCreate }: { onUpload: () => void; onCreate: () => void }) {
  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const addMenuRef = useRef<HTMLDivElement>(null);
  useClickOutside(addMenuRef, () => setAddMenuOpen(false), addMenuOpen);
  return (
    <div className="relative" ref={addMenuRef}>
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={addMenuOpen}
        className="flex h-9 items-center gap-1.5 rounded-lg bg-[var(--primary)] px-3.5 text-sm font-medium text-[var(--primary-fg)] hover:bg-[var(--primary-hover)]"
        onClick={() => setAddMenuOpen((v) => !v)}
      >
        <PlusIcon className="h-4 w-4" /> Add <ChevronDownIcon className="h-3.5 w-3.5" />
      </button>
      {addMenuOpen && (
        <div
          role="menu"
          className="absolute right-0 top-full z-20 mt-1 min-w-48 rounded-[10px] border border-[var(--border)] bg-[var(--panel-bg)] py-1 shadow-[var(--shadow)]"
        >
          <button
            type="button"
            role="menuitem"
            className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-[var(--card-bg)]"
            onClick={() => {
              setAddMenuOpen(false);
              onUpload();
            }}
          >
            <UploadIcon className="h-3.5 w-3.5" /> Upload a plugin or skill
          </button>
          <button
            type="button"
            role="menuitem"
            className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-[var(--card-bg)]"
            onClick={() => {
              setAddMenuOpen(false);
              onCreate();
            }}
          >
            <PencilIcon className="h-3.5 w-3.5" /> Create with Coscribe
          </button>
        </div>
      )}
    </div>
  );
}
