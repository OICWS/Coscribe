import { useMemo, useState } from "react";
import { diffLines, diffStat, withContext, type DiffRow } from "../lib/lineDiff";
import { Disclosure } from "./chatlog/SummaryLabel";

const ROW_TINT = { same: "", add: "bg-emerald-500/10", del: "bg-[var(--danger)]/10" };
const MARK_TINT = { add: "bg-emerald-500/25", del: "bg-[var(--danger)]/25" };

function Text({ row }: { row: DiffRow }) {
  if (row.kind === "same" || !row.mark || row.mark[0] === row.mark[1]) return <>{row.text}</>;
  const [start, end] = row.mark;
  return (
    <>
      {row.text.slice(0, start)}
      <span className={`rounded-sm ${MARK_TINT[row.kind]}`}>{row.text.slice(start, end)}</span>
      {row.text.slice(end)}
    </>
  );
}

/** How the plan changed, as a command-style row that opens to the lines:
 * "Created plan +19 -0" for the first version, "Updated plan +10 -11" after
 * a revision. */
export function PlanDiff({ before, after }: { before: string; after: string }) {
  const [open, setOpen] = useState(false);
  const rows = useMemo(() => diffLines(before, after), [before, after]);
  const { added, removed } = diffStat(rows);
  const entries = useMemo(() => (open ? withContext(rows) : []), [open, rows]);
  if (added === 0 && removed === 0) return null;

  return (
    <div className="w-full text-sm">
      <button
        type="button"
        aria-expanded={open}
        className="inline-flex max-w-full items-center gap-1.5 text-left text-[var(--muted)] hover:text-[var(--fg)]"
        onClick={() => setOpen(!open)}
      >
        {before === "" ? "Created plan" : "Updated plan"}
        <span className="font-mono text-[0.85em] tabular-nums">
          {added > 0 && <span className="text-emerald-600 dark:text-emerald-400">+{added}</span>}
          {removed > 0 && <span className="ml-1 text-[var(--danger)]">-{removed}</span>}
        </span>
        <Disclosure open={open} />
      </button>
      {open && (
        <div className="mt-2 max-h-96 overflow-auto rounded-xl border border-[var(--border)] bg-[var(--bg)] py-1.5 font-mono text-xs leading-relaxed">
          {entries.map((entry, index) =>
            entry.kind === "gap" ? (
              <div key={index} className="px-3 py-0.5 text-[var(--muted)]">
                ⋯ {entry.hidden} unchanged {entry.hidden === 1 ? "line" : "lines"}
              </div>
            ) : (
              <div key={index} className={`flex ${ROW_TINT[entry.kind]}`}>
                <span className="w-9 shrink-0 select-none pr-1.5 text-right text-[var(--muted)]">{entry.newNo ?? entry.oldNo}</span>
                <span className="w-4 shrink-0 select-none text-center text-[var(--muted)]">
                  {entry.kind === "add" ? "+" : entry.kind === "del" ? "-" : ""}
                </span>
                <span className="min-w-0 flex-1 whitespace-pre-wrap break-words pr-3">
                  <Text row={entry} />
                </span>
              </div>
            ),
          )}
        </div>
      )}
    </div>
  );
}
