import { capitalize, formatRunTime } from "../lib/runLabels";
import type { ConnectorCheckState, ScheduledTask } from "../types/settings";
import { WebhookAddress } from "./WebhookAddress";

// Above the runs of a task that starts on something from outside: how a connector task's latest
// check went (decision 0039), or where a webhook task's events go and how the latest went (decision
// 0040), and what started no run, each with why, since it has no run of its own to open.

function lastCheckWords(check: NonNullable<ConnectorCheckState["last_check"]>): string {
  const when = `Last checked ${formatRunTime(check.at)}`;
  if (check.error) return `${when}: ${check.error}`;
  if (check.found === 0) return `${when}: nothing new`;
  const held = check.held ? `, ${check.held} waiting for the next checks` : "";
  return `${when}: ${check.found} new${held}`;
}

function Missed({ missed }: { missed: ConnectorCheckState["missed"] }) {
  if (missed.length === 0) return null;
  return (
    <ul className="flex flex-col">
      {[...missed].reverse().map((entry, index) => (
        <li key={index} className="truncate text-[var(--muted)]" title={entry.reason}>
          {capitalize(formatRunTime(entry.at))} · “{entry.item}” didn't run: {entry.reason}
        </li>
      ))}
    </ul>
  );
}

/** Where a webhook task's events go, above its runs (decision 0040). */
export function WebhookSection({ task }: { task: ScheduledTask }) {
  if (task.schedule.kind !== "webhook") return null;
  return (
    <div>
      <h2 className="mb-2 text-sm font-medium">Where events come from</h2>
      <WebhookAddress taskId={task.trigger_id} inputs={task.workflow?.inputs ?? []} />
    </div>
  );
}

function WebhookNote({ task }: { task: ScheduledTask }) {
  const last = task.webhook?.last_event;
  return (
    <div className="mb-2 flex flex-col gap-1 text-[13px]" data-testid="webhook-note">
      <p className={last && last.status >= 400 ? "text-[var(--danger)]" : "text-[var(--muted)]"}>
        {last ? `Last event ${formatRunTime(last.at)}: ${last.message}` : "No event yet."}
      </p>
      <Missed missed={task.webhook?.missed ?? []} />
    </div>
  );
}

export function TriggerNote({ task }: { task: ScheduledTask }) {
  if (task.schedule.kind === "webhook") return <WebhookNote task={task} />;
  const state = task.connector_check;
  if (task.schedule.kind !== "connector" || !state) return null;
  const check = state.last_check;
  return (
    <div className="mb-2 flex flex-col gap-1 text-[13px]" data-testid="connector-check">
      <p className={check?.error ? "text-[var(--danger)]" : "text-[var(--muted)]"}>
        {check ? lastCheckWords(check) : "Not checked yet: the first check takes what is there as seen."}
      </p>
      <Missed missed={state.missed} />
    </div>
  );
}
