import type { ProgressItem, ProgressStatus } from "../lib/workflowProgress";

const RING = "h-[18px] w-[18px] shrink-0";

/** One item's state: a filled tick when done, a spinner while it runs (two
 * spinners are two items in parallel), a ring with three dots when it is
 * stopped on the person, a dashed circle when it has not started. */
export function TaskStatusIcon({
  status,
  live = false,
  plain = false,
  waiting = false,
}: {
  status: ProgressStatus;
  live?: boolean;
  plain?: boolean;
  waiting?: boolean;
}) {
  if (status === "completed" && plain) {
    return (
      <svg viewBox="0 0 18 18" className={`${RING} text-[var(--fg)]`} aria-label="Done" role="img">
        <path d="M3.5 9.4l3.6 3.6 7.4-8" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (status === "completed") {
    return (
      <svg viewBox="0 0 18 18" className={`${RING} text-[var(--muted)]`} aria-label="Done" role="img">
        <circle cx="9" cy="9" r="8" fill="currentColor" />
        <path d="M5.5 9.2l2.4 2.4 4.6-5" fill="none" stroke="var(--bg)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (status === "in_progress" && !waiting) {
    return (
      <svg viewBox="0 0 18 18" className={`${RING} text-[var(--fg)] ${live ? "motion-safe:animate-spin" : ""}`} aria-label="Running" role="img">
        <circle cx="9" cy="9" r="7.4" fill="none" stroke="currentColor" strokeOpacity="0.2" strokeWidth="1.6" />
        <path d="M9 1.6a7.4 7.4 0 0 1 7.4 7.4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    );
  }
  if (status === "in_progress") {
    return (
      <svg viewBox="0 0 18 18" className={`${RING} text-[var(--fg)]`} aria-label="Waiting" role="img">
        <circle cx="9" cy="9" r="7.4" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <circle cx="5.6" cy="9" r="1" fill="currentColor" />
        <circle cx="9" cy="9" r="1" fill="currentColor" />
        <circle cx="12.4" cy="9" r="1" fill="currentColor" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 18 18" className={`${RING} text-[var(--muted)]`} aria-label="To do" role="img">
      <circle cx="9" cy="9" r="7.4" fill="none" stroke="currentColor" strokeWidth="1.4" strokeDasharray="2.6 2.6" />
    </svg>
  );
}

/** The items of a task list, one per line. In the Plan panel (`strike`) a
 * finished one has a plain tick and is struck through; in the conversation it
 * is a filled tick and only greyed. */
export function TaskList({ tasks, strike = false, live = false }: { tasks: ProgressItem[]; strike?: boolean; live?: boolean }) {
  return (
    <ol className="flex flex-col gap-2.5">
      {tasks.map((task) => (
        <li key={task.id} className="flex items-start gap-2.5 text-[15px] leading-6">
          <span className="mt-[3px]">
            <TaskStatusIcon status={task.status} live={live} plain={strike} />
          </span>
          <span
            className={`min-w-0 [overflow-wrap:anywhere] ${
              task.status === "completed" ? (strike ? "line-through" : "text-[var(--muted)]") : ""
            }`}
          >
            {task.content}
          </span>
        </li>
      ))}
    </ol>
  );
}
