import { useEffect, useRef } from "react";
import type { DraftStep } from "../lib/planTaskDraft";
import { ArrowDownIcon, ArrowUpIcon, PlusIcon, TrashIcon } from "./icons";

const ICON_BUTTON =
  "flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)] disabled:opacity-30 disabled:hover:bg-transparent";

/** The task list of a plan waiting for review, editable: untick a step to leave it out,
 * reword, reorder, delete or add one. The plan's answer carries the result. */
export function PlanTaskEditor({ steps, onSteps }: { steps: DraftStep[]; onSteps: (steps: DraftStep[]) => void }) {
  const inputs = useRef(new Map<string, HTMLInputElement>());
  // An added step is focused once it has rendered.
  const focusNext = useRef<string | null>(null);

  useEffect(() => {
    if (focusNext.current === null) return;
    inputs.current.get(focusNext.current)?.focus();
    focusNext.current = null;
  });

  const change = (key: string, patch: Partial<DraftStep>) =>
    onSteps(steps.map((step) => (step.key === key ? { ...step, ...patch } : step)));
  const move = (index: number, by: -1 | 1) => {
    const next = [...steps];
    [next[index], next[index + by]] = [next[index + by], next[index]];
    onSteps(next);
  };
  const add = () => {
    const key = `new-${crypto.randomUUID()}`;
    focusNext.current = key;
    onSteps([...steps, { key, content: "", included: true }]);
  };

  return (
    <div className="flex flex-col gap-1">
      <ol className="flex flex-col gap-1">
        {steps.map((step, index) => (
          <li key={step.key} className="group flex items-center gap-1.5 rounded-lg px-1 py-0.5 hover:bg-[var(--card-bg)]">
            <input
              type="checkbox"
              aria-label={`Do step ${index + 1}`}
              className="h-4 w-4 shrink-0 accent-[var(--primary)]"
              checked={step.included}
              onChange={(event) => change(step.key, { included: event.target.checked })}
            />
            <input
              ref={(el) => {
                if (el) inputs.current.set(step.key, el);
                else inputs.current.delete(step.key);
              }}
              aria-label={`Step ${index + 1}`}
              placeholder="Describe the step"
              className={`min-w-0 flex-1 rounded-md border border-transparent bg-transparent px-1.5 py-1 text-[15px] outline-none focus:border-[var(--accent)] focus:bg-[var(--bg)] ${
                step.included ? "" : "text-[var(--muted)] line-through"
              }`}
              value={step.content}
              onChange={(event) => change(step.key, { content: event.target.value })}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.nativeEvent.isComposing && index === steps.length - 1) {
                  event.preventDefault();
                  add();
                }
              }}
            />
            <span className="flex shrink-0 items-center opacity-60 group-focus-within:opacity-100 group-hover:opacity-100">
              <button type="button" aria-label={`Move step ${index + 1} up`} className={ICON_BUTTON} disabled={index === 0} onClick={() => move(index, -1)}>
                <ArrowUpIcon className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                aria-label={`Move step ${index + 1} down`}
                className={ICON_BUTTON}
                disabled={index === steps.length - 1}
                onClick={() => move(index, 1)}
              >
                <ArrowDownIcon className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                aria-label={`Delete step ${index + 1}`}
                className={ICON_BUTTON}
                onClick={() => onSteps(steps.filter((other) => other.key !== step.key))}
              >
                <TrashIcon className="h-3.5 w-3.5" />
              </button>
            </span>
          </li>
        ))}
      </ol>
      <button
        type="button"
        className="mt-1 inline-flex w-fit items-center gap-1.5 rounded-md px-1.5 py-1 text-[14px] text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
        onClick={add}
      >
        <PlusIcon className="h-3.5 w-3.5" />
        Add a step
      </button>
    </div>
  );
}
