import { useMemo, useState, type ReactNode } from "react";
import { folderName } from "../lib/folderName";
import { removeFromTask, TaskReachContext, useTaskReach } from "../lib/taskReach";
import { CloseIcon, FolderIcon } from "./icons";

function Line({ name, title, note, onRemove }: { name: string; title?: string; note: string; onRemove?: () => void }) {
  return (
    <li className="flex min-w-0 items-center gap-2 text-sm">
      <FolderIcon className="h-3.5 w-3.5 shrink-0 text-[var(--muted)]" />
      <span className="min-w-0 truncate" title={title}>
        {name}
      </span>
      <span className="shrink-0 text-[var(--muted)]">{note}</span>
      {onRemove && (
        <button
          type="button"
          aria-label={`Remove ${title ?? name}`}
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
          onClick={onRemove}
        >
          <CloseIcon className="h-3 w-3" />
        </button>
      )}
    </li>
  );
}

/** What a task's runs can reach without stopping to ask: its workspace, Settings' Allowed
 * folders, and the folders allowed for this task only, which can be taken back here. */
export function TaskReachSection({ taskId, changed, onChanged }: { taskId: string; changed: string; onChanged: () => void }) {
  const { reach, reload } = useTaskReach(taskId, changed);
  const [error, setError] = useState<string | null>(null);
  if (!reach) return null;
  const remove = async (path: string) => {
    const result = await removeFromTask(taskId, path);
    setError("error" in result ? result.error : null);
    reload();
    onChanged();
  };
  const [main, ...more] = reach.workspace.folders;
  return (
    <section aria-label="What this task can reach" className="rounded-xl border border-[var(--border)] px-4 py-3">
      <h3 className="text-sm font-medium">What this task can reach</h3>
      <ul className="mt-2 flex flex-col gap-1.5">
        <Line
          name={reach.workspace.name}
          title={reach.workspace.folders.join("\n")}
          note={more.length > 0 ? `workspace · ${folderName(main)} +${more.length}` : "workspace"}
        />
        {reach.allowed.length > 0 && (
          <Line
            name={reach.allowed.map((folder) => folderName(folder.path)).join(", ")}
            title={reach.allowed.map((folder) => folder.path).join("\n")}
            note="allowed folders"
          />
        )}
        {reach.task.map((path) => (
          <Line key={path} name={path} title={path} note="this task only · read and write" onRemove={() => void remove(path)} />
        ))}
      </ul>
      {error && (
        <p role="alert" className="mt-2 text-[13px] text-[var(--danger)]">
          {error}
        </p>
      )}
      <p className="mt-2 text-[13px] text-[var(--muted)]">
        A folder allowed while a run waited, or for a folder input, is added here as this task only and can be removed.
      </p>
    </section>
  );
}

/** The saved task a page shows, so its folder inputs are picked from and checked against its reach. */
export function TaskReachProvider({ taskId, onChanged, children }: { taskId: string; onChanged: () => void; children: ReactNode }) {
  const value = useMemo(() => ({ taskId, onChanged }), [taskId, onChanged]);
  return <TaskReachContext.Provider value={value}>{children}</TaskReachContext.Provider>;
}
