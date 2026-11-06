import { useState } from "react";
import type { TaskCardEntry } from "../../lib/taskCard";
import type { ProgressItem } from "../../lib/workflowProgress";
import { TaskStatusIcon } from "../TaskList";
import { Disclosure } from "./SummaryLabel";

function Steps({ tasks, live, waiting = false }: { tasks: ProgressItem[]; live: boolean; waiting?: boolean }) {
  return (
    <div className="w-full rounded-2xl border border-[var(--border)] px-2 py-2.5 text-[15px]">
      {tasks.map((task) => (
        <div key={task.id} className="flex items-start gap-2.5 px-2 py-1.5">
          <span className="mt-[3px]">
            <TaskStatusIcon status={task.status} live={live} waiting={waiting} />
          </span>
          <span className={`min-w-0 flex-1 leading-6 [overflow-wrap:anywhere] ${task.status === "completed" ? "text-[var(--muted)]" : ""}`}>{task.content}</span>
        </div>
      ))}
    </div>
  );
}

/** The task list the model keeps, under the latest call that changed it: the items tick off as
 * the work goes, and once all are done it is one line that opens to them. `waiting`: the turn
 * is stopped on an approval or a question, so the running items wait on the person. */
export function TaskCard({ entry, live, waiting = false }: { entry: TaskCardEntry; live: boolean; waiting?: boolean }) {
  const [open, setOpen] = useState(false);
  const done = entry.tasks.filter((task) => task.status === "completed").length;
  if (entry.done) {
    return (
      <div className="w-full">
        <button type="button" aria-expanded={open} className="flex items-center gap-1.5 text-sm text-[var(--muted)] hover:text-[var(--fg)]" onClick={() => setOpen(!open)}>
          <span>
            ✓ {done} {done === 1 ? "step" : "steps"} done
          </span>
          <Disclosure open={open} />
        </button>
        {open && (
          <div className="mt-2">
            <Steps tasks={entry.tasks} live={false} />
          </div>
        )}
      </div>
    );
  }
  return (
    <div className="w-full">
      <div className="mb-1.5 px-1 text-sm text-[var(--muted)]">
        Steps · {done} of {entry.tasks.length} done
      </div>
      <Steps tasks={entry.tasks} live={live} waiting={waiting} />
    </div>
  );
}
