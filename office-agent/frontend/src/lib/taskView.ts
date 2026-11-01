/** Which way a scheduled task's page reads: plain for most people, every detail for whoever
 * builds workflows. A viewer's own preference, so it stays in this browser. */
export type TaskView = "simple" | "detailed";

const KEY = "coscribe.taskView";

export function loadTaskView(): TaskView {
  try {
    return localStorage.getItem(KEY) === "detailed" ? "detailed" : "simple";
  } catch {
    return "simple";
  }
}

export function saveTaskView(view: TaskView): void {
  try {
    localStorage.setItem(KEY, view);
  } catch {
    // A blocked storage only costs the remembered choice.
  }
}
