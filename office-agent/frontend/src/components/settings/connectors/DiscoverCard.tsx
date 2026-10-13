import type { McpCatalogEntry } from "../../../types/settings";
import { CheckIcon, PlusIcon } from "../../icons";
import { ConnectorIcon } from "../ConnectorIcon";

/** One connector in Discover's grid. */
export function DiscoverCard({
  entry,
  added,
  needsSetup,
  pending,
  onOpen,
  onAdd,
}: {
  entry: McpCatalogEntry;
  added: boolean;
  needsSetup: boolean;
  pending: boolean;
  onOpen: () => void;
  onAdd: () => void;
}) {
  const title = entry.title ?? entry.name;
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Open ${title}`}
      className="relative flex cursor-pointer gap-4 rounded-xl border border-[var(--border)] bg-[var(--card-bg)] p-4 outline-none hover:border-[var(--muted)] focus-visible:border-[var(--focus)]"
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.target !== e.currentTarget) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
    >
      <ConnectorIcon name={entry.name} title={title} size="md" />
      <div className="min-w-0 flex-1 pr-8">
        <div className="text-[15px] font-medium">{title}</div>
        <div className="mt-0.5 line-clamp-2 text-sm text-[var(--fg)]">{entry.description}</div>
        {entry.made_by && (
          <div className="mt-1.5 text-sm text-[var(--muted)]">
            by {entry.made_by}
            {needsSetup && <span className="ml-2 rounded-full bg-[var(--bg)] px-2 py-0.5 text-xs">Needs setup</span>}
          </div>
        )}
      </div>
      {added ? (
        <CheckIcon aria-label="Added" className="absolute right-4 top-4 h-4 w-4 text-[var(--muted)]" />
      ) : (
        <button
          type="button"
          aria-label={`Add ${title}`}
          disabled={pending}
          className={`absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--bg)] hover:bg-[var(--card-bg)] ${
            pending ? "running-wave-ring" : ""
          }`}
          onClick={(e) => {
            e.stopPropagation();
            onAdd();
          }}
        >
          <PlusIcon className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
