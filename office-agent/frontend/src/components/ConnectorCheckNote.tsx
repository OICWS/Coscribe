import { capitalize, formatRunTime } from "../lib/runLabels";
import type { ConnectorCheckState, ScheduledTask } from "../types/settings";

// Above a connector task's runs (decision 0039): how its latest check went, and the new items that
// started no run, each with why, since they have no run of their own to open.

function lastCheckWords(check: NonNullable<ConnectorCheckState["last_check"]>): string {
  const when = `Last checked ${formatRunTime(check.at)}`;
  if (check.error) return `${when}: ${check.error}`;
  if (check.found === 0) return `${when}: nothing new`;
  const held = check.held ? `, ${check.held} waiting for the next checks` : "";
  return `${when}: ${check.found} new${held}`;
}

export function ConnectorCheckNote({ task }: { task: ScheduledTask }) {
  const state = task.connector_check;
  if (task.schedule.kind !== "connector" || !state) return null;
  const check = state.last_check;
  return (
    <div className="mb-2 flex flex-col gap-1 text-[13px]" data-testid="connector-check">
      <p className={check?.error ? "text-[var(--danger)]" : "text-[var(--muted)]"}>
        {check ? lastCheckWords(check) : "Not checked yet: the first check takes what is there as seen."}
      </p>
      {state.missed.length > 0 && (
        <ul className="flex flex-col">
          {[...state.missed].reverse().map((missed, index) => (
            <li key={index} className="truncate text-[var(--muted)]" title={missed.reason}>
              {capitalize(formatRunTime(missed.at))} · “{missed.item}” didn't run: {missed.reason}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
