import { type ComponentType, type RefObject, useEffect, useMemo, useRef, useState } from "react";
import { SearchIcon } from "../icons";
import { findSettings, matchRange } from "./searchIndex";
import type { SettingsCategory } from "./SettingsModal";

interface SearchCategory {
  id: SettingsCategory;
  label: string;
  icon: ComponentType<{ className?: string }>;
}

type Result =
  | { kind: "category"; key: string; category: SearchCategory }
  | { kind: "setting"; key: string; category: SearchCategory; label: string };

/** The text with the first place the query occurs in blue. */
function Highlighted({ text, query }: { text: string; query: string }) {
  const range = matchRange(text, query.trim());
  if (!range) return <>{text}</>;
  return (
    <>
      {text.slice(0, range[0])}
      <span className="text-[var(--accent)]">{text.slice(range[0], range[1])}</span>
      {text.slice(range[1])}
    </>
  );
}

function ResultList({
  results,
  query,
  active,
  activeItem,
  onHover,
  onPick,
}: {
  results: Result[];
  query: string;
  active: number;
  activeItem: RefObject<HTMLButtonElement | null>;
  onHover: (i: number) => void;
  onPick: (result: Result) => void;
}) {
  return (
    <div
      id="settings-search-results"
      role="listbox"
      className="absolute left-0 right-0 top-[calc(100%+6px)] z-20 max-h-[min(360px,60vh)] overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--panel-bg)] p-1.5 shadow-[var(--shadow)]"
    >
      {results.length === 0 && <div className="px-3 py-2 text-sm text-[var(--muted)]">No matches.</div>}
      {results.map((result, i) => (
        <button
          key={result.key}
          ref={i === active ? activeItem : undefined}
          type="button"
          role="option"
          aria-selected={i === active}
          className={`flex w-full items-center gap-3 rounded-lg px-3 py-1.5 text-left text-[15px] ${
            i === active ? "bg-[var(--card-bg)]" : ""
          }`}
          onMouseEnter={() => onHover(i)}
          onClick={() => onPick(result)}
        >
          <result.category.icon className="h-[18px] w-[18px] shrink-0" />
          <span className="flex min-w-0 flex-col">
            <span className="truncate">
              {result.kind === "category" ? <Highlighted text={result.category.label} query={query} /> : result.category.label}
            </span>
            {result.kind === "setting" && (
              <span className="truncate text-[13px] text-[var(--muted)]">
                <Highlighted text={result.label} query={query} />
              </span>
            )}
          </span>
        </button>
      ))}
    </div>
  );
}

export function SettingsSearch({
  categories,
  onPickCategory,
  onPickSetting,
}: {
  categories: SearchCategory[];
  onPickCategory: (id: SettingsCategory) => void;
  onPickSetting: (id: SettingsCategory, label: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const activeItem = useRef<HTMLButtonElement>(null);

  const results = useMemo<Result[]>(() => {
    const q = query.trim();
    if (!q) return [];
    const byId = new Map(categories.map((c) => [c.id, c]));
    const hits: Result[] = categories
      .filter((c) => matchRange(c.label, q))
      .map((c) => ({ kind: "category", key: c.id, category: c }));
    for (const entry of findSettings(q)) {
      const category = byId.get(entry.category);
      if (category) hits.push({ kind: "setting", key: `${entry.category}/${entry.label}`, category, label: entry.label });
    }
    return hits;
  }, [query, categories]);

  useEffect(() => activeItem.current?.scrollIntoView({ block: "nearest" }), [active]);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const pick = (result: Result) => {
    setOpen(false);
    setQuery("");
    if (result.kind === "category") onPickCategory(result.category.id);
    else onPickSetting(result.category.id, result.label);
  };
  const showList = open && query.trim() !== "";

  return (
    <div ref={box} className="relative">
      <div className="flex h-10 items-center gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--field-bg)] px-3 focus-within:border-[var(--focus)] focus-within:ring-2 focus-within:ring-[var(--focus)]/15">
        <SearchIcon className="h-[18px] w-[18px] shrink-0 text-[var(--muted)]" />
        <input
          role="combobox"
          aria-expanded={showList}
          aria-controls="settings-search-results"
          aria-label="Search settings"
          className="w-full min-w-0 bg-transparent text-[15px] outline-none placeholder:text-[var(--muted)]"
          placeholder="Search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Escape" && showList) {
              // Closes the list, not the whole dialog.
              e.stopPropagation();
              setOpen(false);
            } else if (e.key === "ArrowDown" && results.length > 0) {
              e.preventDefault();
              setOpen(true);
              setActive((i) => Math.min(i + 1, results.length - 1));
            } else if (e.key === "ArrowUp" && results.length > 0) {
              e.preventDefault();
              setActive((i) => Math.max(i - 1, 0));
            } else if (e.key === "Enter" && showList && results[active]) {
              e.preventDefault();
              pick(results[active]);
            }
          }}
        />
      </div>
      {showList && (
        <ResultList results={results} query={query} active={active} activeItem={activeItem} onHover={setActive} onPick={pick} />
      )}
    </div>
  );
}
