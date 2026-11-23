import { ArrowLeftIcon } from "../../icons";
import { ToggleSwitch } from "../../ToggleSwitch";
import { SOURCE_BYLINE, shortDate, type ListEntry } from "./helpers";
import { SkillBadge } from "./badges";
import { SkillMenu } from "./SkillMenu";

type PluginEntry = Extract<ListEntry, { kind: "plugin" }>;

/** An added plugin: what it is, and its skills, each opening its own page. */
export function InstalledPluginView({
  entry,
  onBack,
  onOpenSkill,
  onToggle,
  onRemove,
}: {
  entry: PluginEntry;
  onBack: () => void;
  onOpenSkill: (name: string) => void;
  onToggle: () => void;
  onRemove: () => void;
}) {
  const { info, skills } = entry;
  const byline = info.author ? `By ${info.author}` : SOURCE_BYLINE[entry.source].replace(/^./, (c) => c.toUpperCase());
  return (
    <div className="flex flex-col gap-5">
      <button type="button" className="flex w-fit items-center gap-2 text-[15px] text-[var(--fg)] hover:opacity-70" onClick={onBack}>
        <ArrowLeftIcon className="h-4 w-4" /> Your plugins
      </button>
      <div className="flex items-center gap-4">
        <SkillBadge large />
        <div className="min-w-0 flex-1">
          <div className="truncate text-lg font-semibold">{info.name}</div>
          <div className="text-sm text-[var(--muted)]">
            {byline}
            {info.version && <> &middot; v{info.version}</>} &middot; updated {shortDate(entry.updated)}
          </div>
        </div>
        <ToggleSwitch on={entry.enabled} onClick={onToggle} label={entry.enabled ? "Turn off" : "Turn on"} />
        <SkillMenu label={info.name} enabled={entry.enabled} removable onToggle={onToggle} onRemove={onRemove} />
      </div>
      {info.description && <p className="text-[15px] leading-relaxed">{info.description}</p>}
      <div>
        <div className="mb-2 flex items-center gap-2 text-sm font-medium">
          Skills <span className="rounded-full bg-[var(--card-bg)] px-2 py-0.5 text-xs tabular-nums text-[var(--muted)]">{skills.length}</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {skills.map((skill) => (
            <button
              key={skill.name}
              type="button"
              title={skill.description}
              className={`rounded-full border border-[var(--border)] px-3 py-1 text-[13px] hover:bg-[var(--card-bg)] ${
                skill.enabled ? "" : "text-[var(--muted)] line-through"
              }`}
              onClick={() => onOpenSkill(skill.name)}
            >
              {skill.name}
            </button>
          ))}
        </div>
      </div>
      {info.unused.length > 0 && (
        <p className="text-sm text-[var(--muted)]">
          This plugin also has {formatList(info.unused)}. Coscribe keeps them in its folder but does not use them; when a skill needs an
          outside service, Coscribe offers its own connector in the conversation.
        </p>
      )}
    </div>
  );
}

function formatList(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}
