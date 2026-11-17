import type { ProviderCatalogEntry, ProviderInfo } from "../../../types/settings";
import { ProviderIcon } from "./ProviderIcon";
import { providerKind } from "./kind";

export interface ProviderRow {
  name: string;
  title: string;
  entry: ProviderCatalogEntry | null;
  info: ProviderInfo;
}

// Header and rows share it, so each column lines up with its heading.
const ROW_GRID = "grid grid-cols-[minmax(0,1fr)_minmax(0,12rem)_9rem] items-center gap-4 px-3";

// The server masks all but the last four characters; the row only needs those.
const shortKey = (masked: string | null) => (masked ? `•••• ${masked.slice(-4)}` : "Not set");

/** The providers added, as a table: logo and name, default model, key. */
export function YoursList({
  rows,
  searching,
  onOpen,
  onDiscover,
}: {
  rows: ProviderRow[];
  searching: boolean;
  onOpen: (name: string) => void;
  onDiscover: () => void;
}) {
  if (rows.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-[var(--muted)]">
        {searching ? (
          "No providers match."
        ) : (
          <>
            No providers yet. Add one from{" "}
            <button type="button" className="text-[var(--accent)] hover:underline" onClick={onDiscover}>
              Discover
            </button>
            .
          </>
        )}
      </p>
    );
  }
  return (
    <div className="flex flex-col">
      <div className={`${ROW_GRID} border-b border-[var(--border)] pb-2 text-[13px] text-[var(--muted)]`}>
        <span>Provider</span>
        <span>Default model</span>
        <span>API key</span>
      </div>
      {rows.map((row) => (
        <div key={row.name} className="border-b border-[var(--border)] py-1 last:border-b-0">
          <div
            role="button"
            tabIndex={0}
            aria-label={`Open ${row.title}`}
            className={`${ROW_GRID} cursor-pointer rounded-lg py-2 outline-none hover:bg-[var(--card-bg)] focus-visible:bg-[var(--card-bg)]`}
            onClick={() => onOpen(row.name)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onOpen(row.name);
              }
            }}
          >
            <div className="flex min-w-0 items-center gap-3">
              <ProviderIcon name={row.entry?.name ?? row.name} title={row.title} />
              <span className="truncate text-[15px]">{row.title}</span>
              <span className="shrink-0 rounded-md bg-[var(--card-bg)] px-1.5 py-0.5 text-xs text-[var(--muted)]">
                {row.entry ? providerKind(row.info) : "Custom"}
              </span>
            </div>
            <span className={`truncate text-[15px] ${row.info.default_model ? "" : "text-[var(--muted)]"}`}>
              {row.info.default_model || "Not set"}
            </span>
            <span className="truncate text-[13px] text-[var(--muted)]">{shortKey(row.info.masked_key)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
