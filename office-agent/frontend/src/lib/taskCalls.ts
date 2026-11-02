import { createContext, useContext, useEffect, useState } from "react";
import type { ScheduledTask } from "../types/settings";
import type { RunTaskStep } from "../types/workflow";
import { getScheduledTasks } from "./rest";

/** The task whose workflow is open: its own steps can't run it (decision 0035). */
export const ThisTask = createContext<string | null>(null);

let known: ScheduledTask[] = [];
let fetched: { at: number; list: Promise<ScheduledTask[]> } | null = null;
// Every step on a canvas asks at once; one fetch answers them, and a later page asks again.
const FRESH_MS = 5000;

function listTasks(): Promise<ScheduledTask[]> {
  if (!fetched || Date.now() - fetched.at > FRESH_MS) {
    fetched = { at: Date.now(), list: getScheduledTasks().then((listed) => (known = listed)) };
  }
  return fetched.list;
}

/** The saved workflow tasks a run-task step may run: the last list fetched at once, then a
 * fresh one, so a task saved meanwhile shows up. */
export function useCallableTasks(): ScheduledTask[] {
  const self = useContext(ThisTask);
  const [tasks, setTasks] = useState(known);
  useEffect(() => {
    let live = true;
    listTasks()
      .then((listed) => {
        if (live) setTasks(listed);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);
  return tasks.filter((task) => task.workflow && task.workflow.steps.length > 0 && task.trigger_id !== self);
}

/** The task names by id, for the words that describe a run-task step. */
export function useTaskNames(): Map<string, string> {
  const tasks = useCallableTasks();
  return new Map(tasks.map((task) => [task.trigger_id, task.name]));
}

/** The inputs a run-task step gives, in the order the called task asks for them. */
export function givenInputs(step: RunTaskStep, task: ScheduledTask | undefined): [string, string, string][] {
  const asked = task?.workflow?.inputs ?? [];
  const named = asked.map((input): [string, string, string] => [
    input.name,
    input.label || input.name,
    step.inputs[input.name] ?? "",
  ]);
  const extra = Object.entries(step.inputs).filter(([name]) => !asked.some((input) => input.name === name));
  return [...named, ...extra.map(([name, value]): [string, string, string] => [name, name, value])];
}
