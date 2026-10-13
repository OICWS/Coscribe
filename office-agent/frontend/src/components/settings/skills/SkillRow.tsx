import type { SkillInfo } from "../../../types/settings";
import { SOURCE_BYLINE, shortDate } from "./helpers";
import { SkillBadge } from "./badges";
import { SkillMenu } from "./SkillMenu";

export function SkillRow({
  skill,
  onOpen,
  onToggle,
  onRemove,
}: {
  skill: SkillInfo;
  onOpen: () => void;
  onToggle: () => void;
  onRemove: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Open ${skill.name}`}
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
      <div className={`min-w-0 flex-1 ${skill.enabled ? "" : "opacity-55"}`}>
        <div className="flex items-center gap-2">
          <span className="truncate text-[15px]">{skill.name}</span>
          {!skill.enabled && (
            <span className="shrink-0 rounded bg-[var(--card-bg)] px-1.5 py-0.5 text-[11px] text-[var(--muted)]">Off</span>
          )}
        </div>
        <div className="truncate text-sm text-[var(--muted)]" title={skill.description}>
          {SOURCE_BYLINE[skill.source]} &middot; {skill.description}
        </div>
      </div>
      <span className="shrink-0 text-sm tabular-nums text-[var(--muted)]">{shortDate(skill.updated)}</span>
      <SkillMenu skill={skill} onToggle={onToggle} onRemove={onRemove} />
    </div>
  );
}
