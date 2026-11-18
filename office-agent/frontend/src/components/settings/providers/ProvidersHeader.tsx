import { useRef, useState } from "react";
import { useClickOutside } from "../../../lib/useClickOutside";
import { ChevronDownIcon, PlusIcon, SearchIcon } from "../../icons";

export type ProvidersView = "yours" | "discover";

const segment = (on: boolean) =>
  `rounded-md px-3.5 py-1 text-[15px] ${
    on ? "bg-[var(--bg)] text-[var(--fg)] shadow-sm ring-1 ring-[var(--border)]" : "text-[var(--muted)] hover:text-[var(--fg)]"
  }`;
const menuItem = "flex w-full px-3 py-1.5 text-left text-sm hover:bg-[var(--card-bg)]";

/** The title, Yours / Discover, search and the Add menu, laid out as Connectors' are. */
export function ProvidersHeader({
  view,
  onView,
  search,
  onSearch,
  onAddCustom,
}: {
  view: ProvidersView;
  onView: (view: ProvidersView) => void;
  search: string;
  onSearch: (text: string) => void;
  onAddCustom: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  useClickOutside(menuRef, () => setMenuOpen(false), menuOpen);
  return (
    <div className="flex flex-wrap items-center gap-3">
      <h2 className="mr-1 text-[22px] font-semibold">Providers</h2>
      <div className="flex rounded-lg bg-[var(--card-bg)] p-0.5">
        <button type="button" aria-pressed={view === "yours"} className={segment(view === "yours")} onClick={() => onView("yours")}>
          Yours
        </button>
        <button type="button" aria-pressed={view === "discover"} className={segment(view === "discover")} onClick={() => onView("discover")}>
          Discover
        </button>
      </div>
      <div className="flex-1" />
      <div className="flex h-9 w-60 items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-3 focus-within:border-[var(--focus)] focus-within:ring-2 focus-within:ring-[var(--focus)]/15">
        <SearchIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
        <input
          aria-label="Search providers"
          className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--muted)]"
          placeholder="Search providers"
          value={search}
          onChange={(e) => onSearch(e.target.value)}
        />
      </div>
      <div className="relative" ref={menuRef}>
        <button
          type="button"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          className="flex h-9 items-center gap-1.5 rounded-lg bg-[var(--primary)] px-3.5 text-sm font-medium text-[var(--primary-fg)] hover:bg-[var(--primary-hover)]"
          onClick={() => setMenuOpen((v) => !v)}
        >
          <PlusIcon className="h-4 w-4" /> Add <ChevronDownIcon className="h-3.5 w-3.5" />
        </button>
        {menuOpen && (
          <div
            role="menu"
            className="absolute right-0 top-full z-20 mt-1 min-w-52 rounded-[10px] border border-[var(--border)] bg-[var(--panel-bg)] py-1 shadow-[var(--shadow)]"
          >
            <button
              type="button"
              role="menuitem"
              className={menuItem}
              onClick={() => {
                setMenuOpen(false);
                onView("discover");
              }}
            >
              Browse Discover
            </button>
            <button
              type="button"
              role="menuitem"
              className={menuItem}
              onClick={() => {
                setMenuOpen(false);
                onAddCustom();
              }}
            >
              Add custom provider
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
