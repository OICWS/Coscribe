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

/** A longer list shows this many items until the person opens it. */
const SHOWN_STEPS = 5;
/** How many finished items stay in view above the first open one. */
const DONE_IN_VIEW = 3;

/** The items in view while a long list is closed: a window starting a few finished items above the
 * first open one, so the card shows what was just done and what comes next. */
export function stepsInView(tasks: ProgressItem[]): ProgressItem[] {
  if (tasks.length <= SHOWN_STEPS) return tasks;
  const firstOpen = tasks.findIndex((task) => task.status !== "completed");
  const anchor = firstOpen === -1 ? tasks.length : firstOpen;
  const start = Math.min(Math.max(anchor - DONE_IN_VIEW, 0), tasks.length - SHOWN_STEPS);
  return tasks.slice(start, start + SHOWN_STEPS);
}

function Steps({ tasks, bound, live, waiting = false, collapse = false }: { tasks: ProgressItem[]; bound: TaskCardEntry["bound"]; live: boolean; waiting?: boolean; collapse?: boolean }) {
  const background = useContext(BackgroundTasks);
  const [all, setAll] = useState(false);
  const shown = collapse && !all ? stepsInView(tasks) : tasks;
  const hidden = tasks.length - shown.length;
  return (
    <div className="w-full rounded-2xl border border-[var(--border)] px-2 py-2.5 text-[15px]">
      {shown.map((task) => {
        const started = bound[task.id] ?? [];
        const states = started.map((taskId) => background.statuses[taskId]);
        return (
          <div key={task.id} className="group/step flex items-start gap-2.5 px-2 py-1.5">
            <span className="mt-[3px]">
              <TaskStatusIcon status={task.status} live={live} waiting={waiting || states.includes("needs_approval")} />
            </span>
            <span className={`min-w-0 flex-1 leading-6 [overflow-wrap:anywhere] ${task.status === "completed" ? "text-[var(--muted)]" : ""}`}>
              {/* Struck through when done; resting the pointer on the item lifts the line so it reads plainly. */}
              <span className={task.status === "completed" ? "line-through group-hover/step:no-underline" : ""}>{task.content}</span>
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
      {collapse && tasks.length > SHOWN_STEPS && (
        <button
          type="button"
          aria-expanded={all}
          className="mx-2 mt-1 text-sm text-[var(--muted)] hover:text-[var(--fg)]"
          onClick={() => setAll(!all)}
        >
          {all ? "Show less" : `Show ${hidden} more`}
        </button>
      )}
    </div>
  );
}

/** The task list the model keeps, under the latest call that changed it: the items tick off as
 * the work goes (a long list shows a few around the current one and opens to the rest), and once
 * all are done it is one line that opens to them. `waiting`: the turn
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
      <Steps tasks={entry.tasks} bound={entry.bound} live={live} waiting={waiting} collapse />
    </div>
  );
}
