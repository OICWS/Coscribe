import type { Step } from "./DocPanel";
import type { SaveState } from "./useDocSave";

const bar = "flex items-center gap-3 border-b border-[var(--border)] px-4 py-2 text-xs";
const small = "rounded-md border border-[var(--border)] px-2 py-1 text-[var(--fg)] hover:bg-[var(--card-bg)]";

/** What the person is told above the page: a comment that failed, a save that did not go through, and a
 * change made behind the editor's back with the offer to take it back. */
export function DocNotices({
  problem,
  onDismissProblem,
  state,
  onReload,
}: {
  problem: string | null;
  onDismissProblem: () => void;
  state: SaveState;
  onReload: () => void;
}) {
  return (
    <>
      {problem && (
        <div className={`${bar} text-[var(--danger)]`} role="alert">
          <span className="flex-1">{problem}</span>
          <button type="button" className={small} onClick={onDismissProblem}>
            Dismiss
          </button>
        </div>
      )}
      {(state.kind === "conflict" || state.kind === "error") && (
        <div className={`${bar} text-[var(--danger)]`}>
          <span className="flex-1">{state.kind === "conflict" ? "This document changed since you opened it. Your latest edits are not saved." : state.message}</span>
          {state.kind === "conflict" && (
            <button type="button" className={small} onClick={onReload}>
              Reload
            </button>
          )}
        </div>
      )}
    </>
  );
}

export function DocStepControl({ step, onStep, onDismiss }: {
  step: Step;
  onStep: (taken: Extract<Step, { to: string }>) => void;
  onDismiss: () => void;
}) {
  const label = step.kind === "undo" ? "Undo the last document change" : "Redo the last document change";
  return <div className="flex min-w-0 shrink items-center gap-1 text-xs" role="group" aria-label="Change to this document">
    {step.kind === "failed" ? <span className="truncate text-[var(--danger)]" title={step.message}>{step.message}</span> :
      <button type="button" title={label} className={small} onClick={() => onStep(step)}>{step.kind === "undo" ? "Undo" : "Redo"}</button>}
    <button type="button" aria-label="Dismiss document change" className="rounded px-1.5 py-1 text-[var(--muted)] hover:bg-[var(--card-bg)]" onClick={onDismiss}>×</button>
  </div>;
}
