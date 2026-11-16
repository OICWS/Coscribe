import { useContext, useState } from "react";
import type { TaskCardEntry } from "../../lib/taskCard";
import type { ProgressItem } from "../../lib/workflowProgress";
import { TaskStatusIcon } from "../TaskList";
import { BackgroundTasks } from "./contexts";
import { Disclosure } from "./SummaryLabel";

// An agent's and a script's states, in the words the Background tasks panel uses.
const STATE_WORDS: Readonly<Record<string, string>> = {
  running: "running",
  needs_approval: "needs approval",
  succeeded: "done",
  failed: "failed",
  timed_out: "timed out",
  stopped: "stopped",
  killed: "stopped",
  interrupted: "stopped",
};
const FAILED = new Set(["failed", "timed_out"]);

function Steps({ tasks, bound, live, waiting = false }: { tasks: ProgressItem[]; bound: TaskCardEntry["bound"]; live: boolean; waiting?: boolean }) {
  const background = useContext(BackgroundTasks);
  return (
    <div className="w-full rounded-2xl border border-[var(--border)] px-2 py-2.5 text-[15px]">
      {tasks.map((task) => {
        const started = bound[task.id] ?? [];
        const states = started.map((taskId) => background.statuses[taskId]);
        return (
          <div key={task.id} className="flex items-start gap-2.5 px-2 py-1.5">
            <span className="mt-[3px]">
              <TaskStatusIcon status={task.status} live={live} waiting={waiting || states.includes("needs_approval")} />
            </span>
            <span className={`min-w-0 flex-1 leading-6 [overflow-wrap:anywhere] ${task.status === "completed" ? "text-[var(--muted)]" : ""}`}>
              {task.content}
              {states.some((state) => FAILED.has(state)) && <span className="ml-2 text-[13px] text-[var(--danger)]">A background task failed</span>}
              {started.map((taskId, i) => (
                <button
                  key={taskId}
                  type="button"
                  className="block text-left text-[13px] leading-5 text-[var(--muted)] underline-offset-2 hover:text-[var(--fg)] hover:underline"
                  onClick={() => background.open(taskId)}
                >
                  Background task{started.length > 1 ? ` ${i + 1}` : ""}
                  {states[i] ? ` · ${STATE_WORDS[states[i]] ?? states[i].replace("_", " ")}` : ""}
                </button>
              ))}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/** The task list the model keeps, under the latest call that changed it: the items tick off as
 * the work goes, and once all are done it is one line that opens to them. `waiting`: the turn
 * is stopped on an approval or a question, so the running items wait on the person. An item
 * lists the background tasks it started; one that waits for approval makes the item wait too. */
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
            <Steps tasks={entry.tasks} bound={entry.bound} live={false} />
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
      <Steps tasks={entry.tasks} bound={entry.bound} live={live} waiting={waiting} />
    </div>
  );
}
