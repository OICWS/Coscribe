import type { ProviderCatalogEntry } from "../../../types/settings";
import { CheckIcon, PlusIcon } from "../../icons";
import { ProviderIcon } from "./ProviderIcon";
import { providerKind } from "./kind";

/** One provider in Discover's grid. */
export function ProviderCard({ entry, added, onOpen }: { entry: ProviderCatalogEntry; added: boolean; onOpen: () => void }) {
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Open ${entry.title}`}
      className="relative flex cursor-pointer gap-4 rounded-xl border border-transparent bg-[color-mix(in_srgb,var(--card-bg)_45%,var(--bg))] p-4 outline-none hover:border-[var(--border-hover)] focus-visible:border-[var(--focus)]"
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.target !== e.currentTarget) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
    >
      <ProviderIcon name={entry.name} title={entry.title} size="md" />
      <div className="min-w-0 flex-1 pr-8">
        <div className="text-[15px] font-medium">{entry.title}</div>
        <div className="mt-0.5 line-clamp-2 text-sm text-[var(--fg)]">{entry.description}</div>
        <div className="mt-1.5 text-sm text-[color-mix(in_srgb,var(--fg)_60%,var(--bg))]">{providerKind(entry)}</div>
      </div>
      {added ? (
        <CheckIcon aria-label="Added" className="absolute right-4 top-4 h-4 w-4 text-[var(--muted)]" />
      ) : (
        <button
          type="button"
          aria-label={`Add ${entry.title}`}
          className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-lg bg-[color-mix(in_srgb,var(--fg)_8%,var(--bg))] text-[var(--fg)] hover:bg-[color-mix(in_srgb,var(--fg)_14%,var(--bg))]"
          onClick={(e) => {
            e.stopPropagation();
            onOpen();
          }}
        >
          <PlusIcon className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
