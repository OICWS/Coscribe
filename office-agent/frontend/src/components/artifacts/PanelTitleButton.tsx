import { ChevronDownIcon } from "../icons";

/** The file's name in a panel's header; it opens the menu of what can be done to the file. */
export function PanelTitleButton({ title, path, onMenu }: { title: string; path: string; onMenu: (anchor: DOMRect) => void }) {
  return (
    <button
      type="button"
      className="flex min-w-0 items-center gap-1 rounded-md px-1 py-0.5 text-[15px] hover:bg-[var(--card-bg)]"
      title={path}
      aria-haspopup="menu"
      onPointerDown={(e) => e.stopPropagation()}
      onClick={(e) => onMenu(e.currentTarget.getBoundingClientRect())}
    >
      <span className="truncate">{title}</span>
      <ChevronDownIcon className="h-3.5 w-3.5 shrink-0 text-[var(--muted)]" />
    </button>
  );
}
