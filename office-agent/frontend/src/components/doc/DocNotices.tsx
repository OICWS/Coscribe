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
  step,
  onStep,
  onDismissStep,
}: {
  problem: string | null;
  onDismissProblem: () => void;
  state: SaveState;
  onReload: () => void;
  step: Step | null;
  onStep: (taken: { kind: "undo" | "redo"; to: string }) => void;
  onDismissStep: () => void;
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
      {step && (
        <div className={`${bar} text-[var(--muted)]`} role="group" aria-label="Change to this document">
          <span className="flex-1">
            {step.kind === "undo" && "This document was changed by Coscribe or another program."}
            {step.kind === "redo" && "The earlier version is back."}
            {step.kind === "failed" && step.message}
          </span>
          {step.kind !== "failed" && (
            <button type="button" className={small} onClick={() => onStep(step)}>
              {step.kind === "undo" ? "Undo" : "Redo"}
            </button>
          )}
          <button type="button" className="rounded-md px-2 py-1 hover:bg-[var(--card-bg)]" onClick={onDismissStep}>
            Dismiss
          </button>
        </div>
      )}
    </>
  );
}
