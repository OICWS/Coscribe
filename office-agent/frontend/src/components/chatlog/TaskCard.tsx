import { useContext, useState } from "react";
import type { TaskCardEntry } from "../../lib/taskCard";
import { type PptxShapeCapture } from "../PptxShapeOverlay";
import { TaskStatusIcon } from "../TaskList";
import { BackgroundTasks } from "./contexts";
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
  const background = useContext(BackgroundTasks);
  const [opened, setOpened] = useState<ReadonlySet<string>>(new Set());
  const toggle = (id: string) =>
    setOpened((prev) => {
      const next = new Set(prev);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  const rows = [...entry.tasks.map((task) => ({ id: task.id, text: task.content, status: task.status })), ...(entry.calls[""] ? [{ id: "", text: "Other steps", status: null }] : [])];

  return (
    <div className="w-full rounded-2xl border border-[var(--border)] px-2 py-2.5 text-[15px]">
      {rows.map((row) => {
        const calls = entry.calls[row.id] ?? [];
        const open = opened.has(row.id);
        const started = entry.bound[row.id] ?? [];
        const states = started.map((taskId) => background.statuses[taskId]);
        const failed = entry.failed.includes(row.id);
        const backgroundFailed = states.some((state) => state === "failed" || state === "timed_out");
        const waiting = entry.waiting.includes(row.id) || states.includes("needs_approval");
        const expandable = calls.length > 0 || started.length > 0;
        return (
          <div key={row.id || "other"}>
            <button
              type="button"
              aria-expanded={expandable ? open : undefined}
              disabled={!expandable}
              className="flex w-full items-start gap-2.5 rounded-lg px-2 py-1.5 text-left"
              onClick={() => toggle(row.id)}
            >
              <span className="mt-[3px]">{row.status && <TaskStatusIcon status={row.status} live={live} waiting={waiting} />}</span>
              <span className={`min-w-0 flex-1 leading-6 [overflow-wrap:anywhere] ${row.status === "completed" || row.status === null ? "text-[var(--muted)]" : ""}`}>
                {row.text}
                {failed && <span className="ml-2 text-[13px] text-[var(--danger)]">A command failed</span>}
                {backgroundFailed && <span className="ml-2 text-[13px] text-[var(--danger)]">A background task failed</span>}
              </span>
              {expandable && (
                <span className="mt-1 text-[var(--muted)]">
                  <Disclosure open={open} />
                </span>
              )}
            </button>
            {open && (
              <div className="pb-2 pl-9 pr-2 pt-1">
                {started.map((taskId) => (
                  <button
                    key={taskId}
                    type="button"
                    className="mb-1 block text-left text-[13px] text-[var(--muted)] underline-offset-2 hover:underline"
                    onClick={() => background.open(taskId)}
                  >
                    Background task{background.statuses[taskId] ? ` · ${background.statuses[taskId].replace("_", " ")}` : ""}
                  </button>
                ))}
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
