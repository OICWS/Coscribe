import { SECTIONS, type ListEntry } from "./helpers";
import { CountBadge } from "./badges";
import { PluginRow } from "./PluginRow";
import { SkillRow } from "./SkillRow";

/** Your plugins, grouped by where they came from; a plugin is one row for all its skills. */
export function YoursSections({
  entries,
  onOpen,
  onToggle,
  onRemove,
}: {
  entries: ListEntry[];
  onOpen: (entry: ListEntry) => void;
  onToggle: (entry: ListEntry) => void;
  onRemove: (entry: ListEntry) => void;
}) {
  return SECTIONS.map(({ source, title }) => {
    const rows = entries.filter((e) => (e.kind === "skill" ? e.skill.source : e.source) === source);
    if (rows.length === 0) return null;
    return (
      <section key={source}>
        <h3 className="flex items-center gap-2 text-[17px] font-medium">
          {title} <CountBadge count={rows.length} />
        </h3>
        <div className="mt-1">
          {rows.map((entry) =>
            entry.kind === "plugin" ? (
              <PluginRow
                key={`plugin:${entry.info.name}`}
                entry={entry}
                onOpen={() => onOpen(entry)}
                onToggle={() => onToggle(entry)}
                onRemove={() => onRemove(entry)}
              />
            ) : (
              <SkillRow
                key={entry.skill.name}
                skill={entry.skill}
                onOpen={() => onOpen(entry)}
                onToggle={() => onToggle(entry)}
                onRemove={() => onRemove(entry)}
              />
            ),
          )}
        </div>
      </section>
    );
  });
}
