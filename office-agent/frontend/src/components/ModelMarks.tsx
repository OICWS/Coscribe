import { modelMarks } from "../lib/modelMarks";
import type { ModelRow } from "../types/settings";

/** A model's capabilities as small muted chips, or as one muted line in a menu (`compact`). */
export function ModelMarks({ row, compact = false }: { row: ModelRow; compact?: boolean }) {
  if (compact) {
    return (
      <span className="truncate text-xs text-[var(--muted)]" title={row.effort_levels.length ? `Effort: ${row.effort_levels.join(", ")}` : undefined}>
        {modelMarks(row, true).join(" · ")}
      </span>
    );
  }
  return (
    <span className="flex flex-wrap gap-1">
      {modelMarks(row).map((mark) => (
        <span key={mark} className="rounded bg-[var(--card-bg)] px-1.5 py-0.5 text-[11px] leading-none text-[var(--muted)]">
          {mark}
        </span>
      ))}
    </span>
  );
}
