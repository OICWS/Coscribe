import { modelMarks } from "../lib/modelMarks";
import type { ModelRow } from "../types/settings";

/** A model's capabilities as small muted chips. */
export function ModelMarks({ row }: { row: ModelRow }) {
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
