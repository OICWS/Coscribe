import { goToThread } from "../../lib/nav";
import type { ScheduledRun } from "../../types/settings";

export const WAITING_FOR_BROWSER = "Waiting for the browser -- another run or test is using it";

/** The way back to the conversation that looked into this run's earlier failure, once a retry has
 * taken the run out of the failed state (whose banner carries its own button). */
export function InvestigationLink({ run }: { run: ScheduledRun }) {
  if (!run.investigation || run.status === "failed") return null;
  const thread = run.investigation;
  return (
    <div className="text-[13px] text-[var(--muted)]" data-testid="run-investigation">
      <button type="button" className="underline hover:text-[var(--fg)]" onClick={() => goToThread(thread)}>
        Open the conversation that looked into the earlier failure
      </button>
    </div>
  );
}
