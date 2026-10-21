import { useState } from "react";
import type { TaskCardEntry } from "../../lib/taskCard";
import { type PptxShapeCapture } from "../PptxShapeOverlay";
import { TaskStatusIcon } from "../TaskList";
import { Disclosure } from "./SummaryLabel";
import { ToolRunGroupView } from "./ToolRuns";

/** The task list the model keeps, in the conversation: one calm card whose
 * items tick off as the work goes. It stands in for the narration and the
 * calls of that stretch; an item opens to the calls made while it was in
 * progress. A failed call is marked on its item. */
export function TaskCard({
  entry,
  live,
  onApprove,
  onPptxShapePicked,
}: {
  entry: TaskCardEntry;
  live: boolean;
  onApprove: (id: string, approved: boolean, scope?: "task") => void;
  onPptxShapePicked: (capture: PptxShapeCapture) => void;
}) {
  const [opened, setOpened] = useState<ReadonlySet<string>>(new Set());
  const toggle = (id: string) =>
    setOpened((prev) => {
      const next = new Set(prev);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  const rows = [...entry.tasks.map((task) => ({ id: task.id, text: task.content, status: task.status })), ...(entry.calls[""] ? [{ id: "", text: "Other steps", status: null }] : [])];

  return (
    <div className="w-full overflow-hidden rounded-xl border border-[var(--border)] text-[15px]">
      {rows.map((row, index) => {
        const calls = entry.calls[row.id] ?? [];
        const open = opened.has(row.id);
        const failed = entry.failed.includes(row.id);
        return (
          <div key={row.id || "other"} className={index > 0 ? "border-t border-[var(--border)]" : ""}>
            <button
              type="button"
              aria-expanded={calls.length > 0 ? open : undefined}
              disabled={calls.length === 0}
              className="flex w-full items-start gap-2.5 px-3.5 py-2.5 text-left enabled:hover:bg-[var(--card-bg)]"
              onClick={() => toggle(row.id)}
            >
              <span className="mt-[3px]">{row.status && <TaskStatusIcon status={row.status} live={live} />}</span>
              <span className={`min-w-0 flex-1 leading-6 [overflow-wrap:anywhere] ${row.status === "completed" || row.status === null ? "text-[var(--muted)]" : ""}`}>
                {row.text}
                {failed && <span className="ml-2 text-[13px] text-[var(--danger)]">A command failed</span>}
              </span>
              {calls.length > 0 && (
                <span className="mt-1 text-[var(--muted)]">
                  <Disclosure open={open} />
                </span>
              )}
            </button>
            {open && (
              <div className="px-3.5 pb-3">
                <ToolRunGroupView
                  group={{ kind: "tool_run", id: `calls-${entry.id}-${row.id}`, items: calls }}
                  live={live}
                  onApprove={onApprove}
                  onPptxShapePicked={onPptxShapePicked}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
