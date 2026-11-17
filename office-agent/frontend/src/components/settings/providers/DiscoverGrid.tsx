import type { ProviderCatalogEntry } from "../../../types/settings";
import { ProviderCard } from "./ProviderCard";

/** The providers Coscribe knows, as cards. */
export function DiscoverGrid({
  entries,
  added,
  search,
  onOpen,
}: {
  entries: ProviderCatalogEntry[];
  added: (entry: ProviderCatalogEntry) => boolean;
  search: string;
  onOpen: (name: string) => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <h3 className="flex items-center gap-2 text-[17px] font-medium">
        Providers <span className="rounded-md bg-[var(--card-bg)] px-1.5 text-xs text-[var(--muted)]">{entries.length}</span>
      </h3>
      {entries.length === 0 ? (
        <p className="py-6 text-center text-sm text-[var(--muted)]">No providers match "{search.trim()}".</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {entries.map((entry) => (
            <ProviderCard key={entry.name} entry={entry} added={added(entry)} onOpen={() => onOpen(entry.name)} />
          ))}
        </div>
      )}
      <p className="text-xs text-[var(--muted)]">
        Any other service with an OpenAI-compatible API can be added with Add &gt; Add custom provider. Pick which model
        Coscribe uses by default on the General page.
      </p>
    </div>
  );
}
