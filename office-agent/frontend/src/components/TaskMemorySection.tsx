import { useEffect, useState } from "react";
import { primaryButton, secondaryButton } from "../lib/formStyles";
import { keptBy, MEMORY_TYPE_LABEL, memoryFromText, memoryPreview, memoryText } from "../lib/memoryWords";
import { getTaskMemory, setTaskMemory } from "../lib/rest";
import { formatRunTime } from "../lib/runLabels";
import type { ScheduledTask } from "../types/settings";
import type { MemoryEntry, TaskMemoryValues } from "../types/workflow";
import { AutoTextarea } from "./workflow/fields";

// What a task remembers from its last finished run (decision 0034), on its page: what the next run
// will read, which a person may correct or clear (the next run then reads the starting value).

function MemoryRow({
  entry,
  kept,
  onSave,
}: {
  entry: MemoryEntry;
  kept: TaskMemoryValues[string] | undefined;
  onSave: (value: unknown) => Promise<string | null>;
}) {
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const save = async (value: unknown) => {
    setSaving(true);
    const problem = await onSave(value);
    setSaving(false);
    setError(problem);
    if (!problem) setText(null);
  };
  const value = kept ? kept.value : entry.initial;
  return (
    <li
      className="flex flex-col gap-1.5 rounded-xl border border-[var(--border)] px-3.5 py-2.5"
      data-testid="memory-row"
    >
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="text-sm font-medium">{entry.label || entry.name}</span>
        <span className="text-xs text-[var(--muted)]">
          {kept
            ? `${keptBy(kept.by)} · ${formatRunTime(kept.at)}`
            : `not kept yet · the next run starts from its first value`}
        </span>
        <span className="flex-1" />
        {text === null && (
          <span className="flex gap-1">
            <button
              type="button"
              className="rounded-md px-2 py-0.5 text-xs text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
              onClick={() => setText(memoryText(value, entry.type))}
            >
              Edit
            </button>
            {kept && (
              <button
                type="button"
                className="rounded-md px-2 py-0.5 text-xs text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
                disabled={saving}
                onClick={() => save(null)}
                title="The next run starts again from the first value"
              >
                Clear
              </button>
            )}
          </span>
        )}
      </div>
      {text === null ? (
        <div className="min-w-0 truncate text-[13px] text-[var(--muted)]" title={memoryText(value, entry.type)}>
          {memoryPreview(value)}
        </div>
      ) : (
        <>
          <AutoTextarea
            label={`${entry.label || entry.name} value`}
            placeholder={entry.type === "list" ? "One item per line" : MEMORY_TYPE_LABEL[entry.type]}
            value={text}
            onChange={setText}
          />
          <div className="flex justify-end gap-2">
            <button type="button" className={secondaryButton} onClick={() => setText(null)}>
              Cancel
            </button>
            <button
              type="button"
              className={primaryButton}
              disabled={saving}
              onClick={() => save(memoryFromText(text, entry.type))}
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </>
      )}
      {error && (
        <p role="alert" className="text-xs text-[var(--danger)]">
          {error}
        </p>
      )}
    </li>
  );
}

/** Shown only for a workflow that declares something to remember. `refresh` changes when a run
 * ends, so the values follow the runs. */
export function TaskMemorySection({ task, refresh }: { task: ScheduledTask; refresh: string }) {
  const declared = task.workflow?.memory ?? [];
  const [kept, setKept] = useState<TaskMemoryValues>({});
  useEffect(() => {
    if (declared.length === 0) return;
    let live = true;
    getTaskMemory(task.trigger_id).then((result) => {
      if (live && !("error" in result)) setKept(result.memory);
    });
    return () => {
      live = false;
    };
  }, [task.trigger_id, declared.length, refresh]);
  if (declared.length === 0) return null;
  const save = async (name: string, value: unknown) => {
    const result = await setTaskMemory(task.trigger_id, name, value);
    if ("error" in result) return result.error;
    setKept(result.memory);
    return null;
  };
  return (
    <div data-testid="task-memory">
      <div className="mb-1 text-sm text-[var(--muted)]">Remembered from the last run</div>
      <ul className="flex flex-col gap-2">
        {declared.map((entry) => (
          <MemoryRow
            key={entry.name}
            entry={entry}
            kept={kept[entry.name]}
            onSave={(value) => save(entry.name, value)}
          />
        ))}
      </ul>
    </div>
  );
}
