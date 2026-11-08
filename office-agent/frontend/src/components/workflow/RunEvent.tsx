import { connectorLabel } from "../../lib/runLabels";
import type { ScheduledRun } from "../../types/settings";

/** The item that started a run, as its connector gave it (decision 0039), or the event a program
 * sent (decision 0040): what the run's inputs were taken from, kept whole for when one of them
 * looks wrong. */
export function RunEvent({ run }: { run: ScheduledRun }) {
  if (!run.event) return null;
  return (
    <details className="text-sm" data-testid="run-event">
      <summary className="cursor-pointer text-[var(--muted)] hover:text-[var(--fg)]">
        {run.source === "webhook"
          ? "Started by an event a program sent"
          : `Started by a new item in ${connectorLabel(run.event.connector ?? "")}`}
      </summary>
      <pre className="mt-1.5 max-h-72 overflow-auto rounded-md bg-[var(--card-bg)] p-2.5 font-mono text-[12px] whitespace-pre-wrap break-all">
        {JSON.stringify(run.event.item, null, 2)}
      </pre>
    </details>
  );
}
