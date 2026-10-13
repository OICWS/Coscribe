import type { SkillPlugin } from "../../../types/settings";
import { CheckIcon } from "../../icons";
import { SkillBadge } from "./badges";

export function PluginCard({ plugin, onOpen }: { plugin: SkillPlugin; onOpen: () => void }) {
  const complete = plugin.added === plugin.skills.length;
  return (
    <button
      type="button"
      className="flex min-w-0 flex-col gap-3 rounded-xl border border-[var(--border)] p-4 text-left hover:bg-[var(--card-bg)]"
      onClick={onOpen}
    >
      <div className="flex items-center gap-3">
        <SkillBadge />
        <div className="min-w-0 flex-1">
          <div className="truncate text-[15px] font-medium">{plugin.title}</div>
          <div className="truncate text-xs text-[var(--muted)]">
            by {plugin.author} &middot; {plugin.skills.length} skills
          </div>
        </div>
        {complete && <CheckIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" aria-label="Added" />}
      </div>
      <p className="line-clamp-3 text-sm leading-relaxed text-[var(--muted)]">{plugin.description}</p>
    </button>
  );
}
