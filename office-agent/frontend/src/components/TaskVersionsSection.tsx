import { useEffect, useState } from "react";
import { getTaskVersions, restoreTaskVersion } from "../lib/rest";
import { formatRunTime } from "../lib/runLabels";
import { compareVersions, VERSION_HOW } from "../lib/versionDiff";
import type { ScheduledTask, TaskVersion } from "../types/settings";
import type { Workflow } from "../types/workflow";
import { ConfirmDialog } from "./ConfirmDialog";

// Every workflow the task was saved with (decision 0035), newest first: one compares with what
// it holds now, and one comes back in a click, as a new version.

const SHOWN = 5;
const CHANGE_WORD = { added: "Added", changed: "Changed", removed: "Removed" } as const;

function howWords(version: TaskVersion): string {
  if (version.how === "restored" && version.from) return `Restored from version ${version.from}`;
  return VERSION_HOW[version.how] ?? "Saved";
}

function Differences({ older, current }: { older: Workflow; current: Workflow }) {
  const diff = compareVersions(older, current);
  const nothing = diff.steps.length + diff.inputs.length + diff.otherwise.length === 0;
  return (
    <div className="mt-2 rounded-lg bg-[var(--card-bg)] px-3 py-2.5 text-[13px]" data-testid="version-diff">
      <div className="mb-1.5 text-xs text-[var(--muted)]">What changed since this version</div>
      {nothing && <p className="text-[var(--muted)]">The steps are the same.</p>}
      <ul className="flex flex-col gap-1">
        {diff.steps.map((change) => (
          <li key={`${change.change}-${change.id}`} className="flex items-baseline gap-2">
            <span
              className={`w-16 shrink-0 text-xs font-medium ${
                change.change === "added"
                  ? "text-[var(--success)]"
                  : change.change === "removed"
                    ? "text-[var(--danger)]"
                    : "text-[var(--muted)]"
              }`}
            >
              {CHANGE_WORD[change.change]}
            </span>
            <span className={change.change === "removed" ? "line-through opacity-70" : undefined}>{change.title}</span>
          </li>
        ))}
        {diff.inputs.length > 0 && (
          <li className="flex items-baseline gap-2">
            <span className="w-16 shrink-0 text-xs font-medium text-[var(--muted)]">Inputs</span>
            <span>{diff.inputs.join(", ")}</span>
          </li>
        )}
        {diff.otherwise.length > 0 && (
          <li className="flex items-baseline gap-2">
            <span className="w-16 shrink-0 text-xs font-medium text-[var(--muted)]">Also</span>
            <span>{diff.otherwise.join(", ")}</span>
          </li>
        )}
      </ul>
    </div>
  );
}

const smallButton =
  "rounded-md px-2 py-0.5 text-xs text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]";

/** One version; `current` is null on the one the task holds now, which has nothing to compare. */
function VersionRow({
  version,
  current,
  comparing,
  onCompare,
  onRestore,
}: {
  version: TaskVersion;
  current: Workflow | null;
  comparing: boolean;
  onCompare: () => void;
  onRestore: () => void;
}) {
  return (
    <li className="rounded-md px-2 py-1.5" data-testid="version-row">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm">
        <span className="font-medium">Version {version.number}</span>
        <span className="text-[var(--muted)]">
          {howWords(version)} · {formatRunTime(version.saved_at)}
        </span>
        {!current && (
          <span className="rounded-full bg-[var(--card-bg)] px-2 py-px text-[11px] text-[var(--muted)]">Current</span>
        )}
        <span className="flex-1" />
        {current && (
          <span className="flex gap-1">
            <button type="button" aria-expanded={comparing} className={smallButton} onClick={onCompare}>
              {comparing ? "Hide changes" : "Compare"}
            </button>
            <button type="button" className={smallButton} onClick={onRestore}>
              Restore
            </button>
          </span>
        )}
      </div>
      {current && comparing && <Differences older={version.workflow} current={current} />}
    </li>
  );
}

export function TaskVersionsSection({ task, onChanged }: { task: ScheduledTask; onChanged: () => void }) {
  const [versions, setVersions] = useState<TaskVersion[]>([]);
  const [all, setAll] = useState(false);
  const [comparing, setComparing] = useState<number | null>(null);
  const [restoring, setRestoring] = useState<TaskVersion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const current = task.workflow;

  useEffect(() => {
    getTaskVersions(task.trigger_id)
      .then((result) => setVersions(result.versions))
      .catch(() => setVersions([]));
  }, [task.trigger_id, task.version]);

  if (!current || versions.length === 0) return null;
  const shown = all ? versions : versions.slice(0, SHOWN);

  const restore = async () => {
    if (!restoring) return;
    const result = await restoreTaskVersion(task.trigger_id, restoring.number);
    if ("error" in result) {
      setError(result.error);
      return;
    }
    setRestoring(null);
    setComparing(null);
    onChanged();
  };

  return (
    <section aria-label="Versions">
      <div className="mb-1 text-sm text-[var(--muted)]">Versions</div>
      <ul className="-mx-2 flex flex-col">
        {shown.map((version, index) => (
          <VersionRow
            key={version.number}
            version={version}
            current={index === 0 ? null : current}
            comparing={comparing === version.number}
            onCompare={() => setComparing(comparing === version.number ? null : version.number)}
            onRestore={() => {
              setError(null);
              setRestoring(version);
            }}
          />
        ))}
      </ul>
      {versions.length > SHOWN && (
        <button
          type="button"
          className="mt-1 text-xs text-[var(--muted)] hover:text-[var(--fg)]"
          onClick={() => setAll(!all)}
        >
          {all ? "Show fewer" : `Show all ${versions.length}`}
        </button>
      )}
      {restoring && (
        <ConfirmDialog
          title={`Restore version ${restoring.number}?`}
          description={
            error ? (
              <span className="text-[var(--danger)]">{error}</span>
            ) : (
              "Its steps replace the current ones, saved as a new version, so you can go back again. Past runs keep their record."
            )
          }
          confirmLabel={error ? "OK" : "Restore"}
          tone="neutral"
          onCancel={() => setRestoring(null)}
          onConfirm={error ? () => setRestoring(null) : restore}
        />
      )}
    </section>
  );
}
