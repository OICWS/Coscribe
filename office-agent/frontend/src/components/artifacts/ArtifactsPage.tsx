import { useState } from "react";
import {
  PAGE_KINDS,
  PAGE_ORDER,
  artifactId,
  countsByKind,
  dayGroups,
  readLayout,
  showArtifact,
  visibleArtifacts,
  writeLayout,
  type Filters,
  type Layout,
  type PageItem,
  type PageKind,
} from "../../lib/artifacts";
import { FilterIcon, SearchIcon } from "../icons";
import { SlideMenu, type MenuEntry } from "../slides/SlideMenu";
import { ArtifactCard, ArtifactRow } from "./ArtifactItems";
import { ArtifactMenu } from "./ArtifactMenu";
import { DesignSystemMenu } from "./DesignSystemMenu";
import { KindTile } from "./ArtifactThumb";
import { ArtifactsIcon, GridViewIcon, ListViewIcon } from "./artifactIcons";
import { NewTiles } from "./NewTiles";
import { useArtifacts } from "./useArtifacts";

type Menu = { kind: "filter"; anchor: DOMRect } | { kind: "item"; anchor: DOMRect; item: PageItem };

const TABS: { value: Filters["tab"]; label: string }[] = [
  { value: "all", label: "All" },
  { value: "pinned", label: "Pinned" },
];

const toolButton = "flex h-9 w-9 items-center justify-center rounded-lg text-[var(--fg)] hover:bg-[var(--card-bg)]";

/** Everything coscribe has made, as cards or as a list by day, with a way to make something new.
 * Opening one goes to the conversation that made it. */
export function ArtifactsPage({ onOpen, onMake }: { onOpen: (item: PageItem) => void; onMake: (kind: PageKind, describe?: boolean) => void }) {
  const { items, error, reload, pins, togglePin } = useArtifacts();
  const [filters, setFilters] = useState<Filters>({ tab: "all", kind: null, query: "" });
  const [layout, setLayout] = useState<Layout>(readLayout);
  const [menu, setMenu] = useState<Menu | null>(null);
  const change = (next: Partial<Filters>) => setFilters((current) => ({ ...current, ...next }));
  const flipLayout = () => {
    const next = layout === "grid" ? "list" : "grid";
    writeLayout(next);
    setLayout(next);
  };

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-[1180px] px-8 pb-16 pt-6">
        <h1 className="text-[34px] font-normal leading-tight" style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}>
          Artifacts
        </h1>
        <Toolbar
          filters={filters}
          layout={layout}
          onChange={change}
          onFlipLayout={flipLayout}
          onFilterMenu={(anchor) => setMenu({ kind: "filter", anchor })}
        />
        <div className="mt-8">
          <NewTiles onMake={onMake} />
        </div>
        <div className="mt-10">
          <Results
            items={items}
            error={error}
            filters={filters}
            layout={layout}
            pins={pins}
            onReload={reload}
            onOpen={onOpen}
            onMenu={(item, anchor) => setMenu({ kind: "item", anchor, item })}
          />
        </div>
      </div>
      {menu?.kind === "filter" && (
        <SlideMenu
          anchor={menu.anchor}
          label="Filter by type"
          width={230}
          entries={filterEntries(filters.kind, countsByKind(items ?? []), (kind) => change({ kind }))}
          onClose={() => setMenu(null)}
        />
      )}
      {menu?.kind === "item" && menu.item.kind === "design-system" && (
        <DesignSystemMenu
          anchor={menu.anchor}
          item={menu.item}
          pinned={pins.has(artifactId(menu.item))}
          onPin={() => togglePin(menu.item)}
          onChanged={reload}
          onClose={() => setMenu(null)}
        />
      )}
      {menu?.kind === "item" && menu.item.kind !== "design-system" && (
        <ArtifactMenu
          anchor={menu.anchor}
          item={menu.item}
          pinned={pins.has(artifactId(menu.item))}
          onPin={() => togglePin(menu.item)}
          open={(reveal) => void showArtifact(menu.item.id, reveal).catch(() => undefined)}
          onChanged={reload}
          onClose={() => setMenu(null)}
        />
      )}
    </div>
  );
}

/** The tabs on the left; search, the layout and the type filter on the right. */
function Toolbar({
  filters,
  layout,
  onChange,
  onFlipLayout,
  onFilterMenu,
}: {
  filters: Filters;
  layout: Layout;
  onChange: (next: Partial<Filters>) => void;
  onFlipLayout: () => void;
  onFilterMenu: (anchor: DOMRect) => void;
}) {
  const [searching, setSearching] = useState(false);
  const closeSearch = () => {
    setSearching(false);
    onChange({ query: "" });
  };
  const layoutTitle = layout === "grid" ? "List view" : "Grid view";
  return (
    <div className="mt-6 flex items-center justify-between gap-4">
      <div role="tablist" className="flex gap-1">
        {TABS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={filters.tab === value}
            className={`rounded-lg px-3 py-1.5 text-[15px] ${filters.tab === value ? "bg-[var(--card-bg)] text-[var(--fg)]" : "text-[var(--muted)] hover:text-[var(--fg)]"}`}
            onClick={() => onChange({ tab: value })}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-1">
        {searching && (
          <input
            autoFocus
            aria-label="Search artifacts"
            placeholder="Search artifacts"
            value={filters.query}
            className="mr-1 h-9 w-56 rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-3 text-sm outline-none focus:border-[var(--focus)]"
            onChange={(e) => onChange({ query: e.target.value })}
            onKeyDown={(e) => e.key === "Escape" && closeSearch()}
          />
        )}
        <button type="button" title="Search" aria-label="Search" aria-pressed={searching} className={toolButton} onClick={() => (searching ? closeSearch() : setSearching(true))}>
          <SearchIcon className="h-[18px] w-[18px]" />
        </button>
        <button type="button" title={layoutTitle} aria-label={layoutTitle} className={toolButton} onClick={onFlipLayout}>
          {layout === "grid" ? <ListViewIcon className="h-[18px] w-[18px]" /> : <GridViewIcon className="h-[18px] w-[18px]" />}
        </button>
        <button
          type="button"
          title="Filter by type"
          aria-label="Filter by type"
          aria-haspopup="menu"
          className={`${toolButton} ${filters.kind ? "bg-[var(--accent-soft)] text-[var(--accent-ink)]" : ""}`}
          onClick={(e) => onFilterMenu(e.currentTarget.getBoundingClientRect())}
        >
          <FilterIcon className="h-[18px] w-[18px]" />
        </button>
      </div>
    </div>
  );
}

/** What is under the toolbar: the artifacts, or why there are none to show. */
function Results({
  items,
  error,
  filters,
  layout,
  pins,
  onReload,
  onOpen,
  onMenu,
}: {
  items: PageItem[] | null;
  error: string | null;
  filters: Filters;
  layout: Layout;
  pins: ReadonlySet<string>;
  onReload: () => void;
  onOpen: (item: PageItem) => void;
  onMenu: (item: PageItem, anchor: DOMRect) => void;
}) {
  const now = new Date();
  const shown = visibleArtifacts(items ?? [], pins, filters);
  const rowProps = (item: PageItem) => ({
    item,
    now,
    pinned: pins.has(artifactId(item)),
    onOpen: () => onOpen(item),
    onMenu: (anchor: DOMRect) => onMenu(item, anchor),
  });
  if (error) {
    return (
      <p className="text-sm text-[var(--muted)]">
        Could not load the artifacts ({error}).{" "}
        <button type="button" className="underline hover:text-[var(--fg)]" onClick={onReload}>
          Try again
        </button>
      </p>
    );
  }
  if (items === null) return <p className="text-sm text-[var(--muted)]">Loading…</p>;
  if (shown.length === 0) return <p className="text-sm text-[var(--muted)]">{emptyText(items.length, filters)}</p>;
  if (layout === "grid") {
    return (
      <div className="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-x-5 gap-y-6">
        {shown.map((item) => (
          <ArtifactCard key={artifactId(item)} {...rowProps(item)} />
        ))}
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-6">
      {dayGroups(shown, pins, now).map((group) => (
        <section key={group.title}>
          <h2 className="mb-1 px-3 text-sm text-[var(--muted)]">{group.title}</h2>
          {group.items.map((item) => (
            <ArtifactRow key={artifactId(item)} {...rowProps(item)} />
          ))}
        </section>
      ))}
    </div>
  );
}

function filterEntries(selected: PageKind | null, counts: Record<PageKind, number>, pick: (kind: PageKind | null) => void): MenuEntry[] {
  return [
    { label: "All types", icon: <ArtifactsIcon className="h-4 w-4" />, checked: selected === null, onSelect: () => pick(null) },
    ...PAGE_ORDER.map((kind) => ({
      label: PAGE_KINDS[kind].label,
      icon: <KindTile kind={kind} size="sm" />,
      hint: String(counts[kind]),
      checked: selected === kind,
      onSelect: () => pick(kind),
    })),
  ];
}

function emptyText(total: number, filters: Filters): string {
  if (total === 0) return "Nothing here yet. The decks, documents and spreadsheets coscribe makes for you appear here.";
  if (filters.tab === "pinned" && !filters.query && !filters.kind) return "Pin an artifact to keep it here.";
  return "No artifact matches.";
}
