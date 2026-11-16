import type { ProgressItem } from "./workflowProgress";

// conversation/approvals.py's PLAN_TASKS_MARKER: the approved list follows it, as JSON.
const PLAN_TASKS_MARKER = "Task list as approved:\n";

/** The task list an approved plan's result gives, when the person edited it, as a field to spread
 * into the plan's chat item: live and in a replayed history it then shows the server's list. */
export function planTasksField(result: string): { tasks?: ProgressItem[] } {
  const at = result.indexOf(PLAN_TASKS_MARKER);
  if (at < 0) return {};
  try {
    const parsed: unknown = JSON.parse(result.slice(at + PLAN_TASKS_MARKER.length));
    if (!Array.isArray(parsed)) return {};
    const tasks = parsed.flatMap((task: Record<string, unknown>): ProgressItem[] =>
      task && typeof task.content === "string" && task.id !== undefined
        ? [{ id: String(task.id), content: task.content, status: task.status === "completed" || task.status === "in_progress" ? task.status : "pending" }]
        : [],
    );
    return { tasks };
  } catch {
    return {};
  }
}
