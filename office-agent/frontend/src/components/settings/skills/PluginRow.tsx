import { SOURCE_BYLINE, shortDate, type ListEntry } from "./helpers";
import { SkillBadge } from "./badges";
import { SkillMenu } from "./SkillMenu";

type PluginEntry = Extract<ListEntry, { kind: "plugin" }>;

/** A plugin in Your plugins: one row for all its skills. */
export function PluginRow({
  entry,
  onOpen,
  onToggle,
  onRemove,
}: {
  entry: PluginEntry;
  onOpen: () => void;
  onToggle: () => void;
  onRemove: () => void;
}) {
  const { info, skills } = entry;
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Open ${info.name}`}
      className="flex w-full cursor-pointer items-center gap-4 border-b border-[var(--border)] py-3.5 text-left outline-none last:border-b-0 focus-visible:bg-[var(--card-bg)]"
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
    >
      <SkillBadge />
      <div className={`min-w-0 flex-1 ${entry.enabled ? "" : "opacity-55"}`}>
        <div className="flex items-center gap-2">
          <span className="truncate text-[15px]">{info.name}</span>
          <span className="shrink-0 rounded bg-[var(--card-bg)] px-1.5 py-0.5 text-[11px] text-[var(--muted)]">
            {skills.length} {skills.length === 1 ? "skill" : "skills"}
          </span>
          {!entry.enabled && (
            <span className="shrink-0 rounded bg-[var(--card-bg)] px-1.5 py-0.5 text-[11px] text-[var(--muted)]">Off</span>
          )}
        </div>
        <div className="truncate text-sm text-[color-mix(in_srgb,var(--fg)_60%,var(--bg))]" title={info.description}>
          {info.author ? `by ${info.author}` : SOURCE_BYLINE[entry.source]}
          {info.description && <> &middot; {info.description}</>}
        </div>
      </div>
      <span className="shrink-0 text-sm tabular-nums text-[color-mix(in_srgb,var(--fg)_60%,var(--bg))]">{shortDate(entry.updated)}</span>
      <SkillMenu label={info.name} enabled={entry.enabled} removable onToggle={onToggle} onRemove={onRemove} />
    </div>
  );
}
