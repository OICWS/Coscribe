import { goToThread } from "../../lib/nav";
import type { ScheduledRun } from "../../types/settings";

export const WAITING_FOR_BROWSER =
  "Waiting for the browser -- another run or test is using it";

/** The way to the conversation that looked into this run's failure: a button in the failed banner
 * (`buttonClass`), a quiet link once a retry has taken the run out of that state. */
export function InvestigationLink({
  run,
  buttonClass,
}: {
  run: ScheduledRun;
  buttonClass?: string;
}) {
  const thread = run.investigation;
  if (!thread || (run.status === "failed") !== (buttonClass !== undefined))
    return null;
  const open = () => goToThread(thread);
  if (buttonClass !== undefined) {
    return (
      <button type="button" className={buttonClass} onClick={open}>
        Open the conversation looking into it
      </button>
    );
  }
  return (
    <div
      className="text-[13px] text-[var(--muted)]"
      data-testid="run-investigation"
    >
      <button
        type="button"
        className="underline hover:text-[var(--fg)]"
        onClick={open}
      >
        Open the conversation that looked into the earlier failure
      </button>
    </div>
  );
}
