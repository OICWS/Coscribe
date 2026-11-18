import { useEffect, useRef, useState } from "react";
import { controlClass } from "../../lib/formStyles";
import { folderName } from "../../lib/folderName";
import { browseDirs, getConfig, updateConfig } from "../../lib/rest";
import { allowForTask, checkReach, useTaskReach, type ReachCheck, type TaskReach } from "../../lib/taskReach";
import { CheckIcon, ChevronDownIcon, FolderIcon, SearchIcon } from "../icons";
import { buildDirEntries, changedDirs } from "../settings/fields";
import { DirBrowserModal } from "../settings/DirBrowserModal";

const item = "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-[13px] hover:bg-[color-mix(in_srgb,var(--border)_50%,var(--card-bg))]";
const heading = "px-2.5 pb-1 pt-2 text-xs font-medium text-[var(--muted)]";

/** Allow everywhere: the folder joins Settings' Allowed folders with read and write. */
async function allowEverywhere(path: string): Promise<{ error: string } | null> {
  try {
    const values = (await getConfig()) as unknown as Record<string, string | null>;
    const entries = buildDirEntries(values);
    const kept = entries.find((entry) => entry.path === path);
    const permission = kept?.permission === "read-write-delete" ? kept.permission : "read-write";
    const changed = changedDirs([...entries.filter((entry) => entry.path !== path), { path, permission }], values);
    if (Object.keys(changed).length > 0) await updateConfig(changed);
    return null;
  } catch {
    return { error: "Couldn't add it to Allowed folders." };
  }
}

/** The workspace's folder's own subfolders, which a folder input most often names. */
function useSubfolders(folder: string): string[] {
  const [names, setNames] = useState<string[]>([]);
  useEffect(() => {
    let live = true;
    void browseDirs(folder)
      .then((result) => live && "directories" in result && setNames(result.directories.map((d) => d.name)))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [folder]);
  return names;
}

function Choice({ label, note, chosen, nested, onPick }: { label: string; note?: string; chosen: boolean; nested?: boolean; onPick: () => void }) {
  return (
    <button type="button" role="menuitemradio" aria-checked={chosen} className={`${item} ${nested ? "pl-8" : ""}`} onClick={onPick}>
      <FolderIcon className="h-3.5 w-3.5 shrink-0 text-[var(--muted)]" />
      <span className={`min-w-0 flex-1 truncate ${chosen ? "font-medium" : ""}`}>{label}</span>
      {note && <span className="shrink-0 text-xs text-[var(--muted)]">{note}</span>}
      {chosen && <CheckIcon className="h-3.5 w-3.5 shrink-0" />}
    </button>
  );
}

/** The folders a task reaches, its workspace's subfolders first, and any other folder. */
function FolderMenu({ reach, value, label, onPick, onBrowse }: { reach: TaskReach; value: string; label: string; onPick: (v: string) => void; onBrowse: () => void }) {
  const [main, ...more] = reach.workspace.folders;
  const subfolders = useSubfolders(main);
  return (
    <div role="menu" aria-label={label} className="absolute left-0 right-0 top-full z-30 mt-1 max-h-72 overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--panel-bg)] p-1.5 shadow-[var(--shadow)]">
      <div className={heading}>Workspace · {reach.workspace.name}</div>
      <Choice label={folderName(main)} chosen={value === main} onPick={() => onPick(main)} />
      {subfolders.map((name) => (
        <Choice key={name} label={name} nested chosen={value === name} onPick={() => onPick(name)} />
      ))}
      {more.map((path) => (
        <Choice key={path} label={folderName(path)} chosen={value === path} onPick={() => onPick(path)} />
      ))}
      {reach.allowed.length > 0 && <div className={heading}>Allowed folders</div>}
      {reach.allowed.map((folder) => (
        <Choice
          key={folder.path}
          label={folderName(folder.path)}
          note={folder.permission === "read" ? "Read only" : "Read and write"}
          chosen={value === folder.path}
          onPick={() => onPick(folder.path)}
        />
      ))}
      {reach.task.length > 0 && <div className={heading}>This task only</div>}
      {reach.task.map((path) => (
        <Choice key={path} label={folderName(path)} chosen={value === path} onPick={() => onPick(path)} />
      ))}
      <div className="my-1 h-px bg-[var(--border)]" />
      <button type="button" role="menuitem" className={item} onClick={onBrowse}>
        <SearchIcon className="h-3.5 w-3.5 shrink-0 text-[var(--muted)]" />
        Choose another folder…
      </button>
    </div>
  );
}

const WHERE: Record<NonNullable<ReachCheck["inside"]>, string> = {
  workspace: "the workspace",
  task: "a folder allowed for this task",
  allowed: "an allowed folder",
};

/** A folder outside the reach, before a run would stop at it: allow it, or pick another. */
function OutsideCard({ check, taskId, onAllowed, onPickAnother }: { check: ReachCheck; taskId: string; onAllowed: () => void; onPickAnother: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const allow = async (everywhere: boolean) => {
    const result = everywhere ? await allowEverywhere(check.path) : await allowForTask(taskId, check.path);
    if (result && "error" in result) setError(result.error);
    else onAllowed();
  };
  const small = "h-8 rounded-md px-3 text-[13px]";
  return (
    <div role="status" className="flex flex-col gap-2 rounded-xl border border-[var(--border)] px-3.5 py-3 text-[13px]">
      <div className="flex items-center gap-2 font-medium">
        <span className="h-[7px] w-[7px] shrink-0 rounded-full bg-[var(--warning)]" />
        <span className="min-w-0 break-all">This task can’t use {check.path} yet</span>
      </div>
      <span className="text-[var(--muted)]">
        {check.exists
          ? "It’s outside the workspace and the allowed folders, so a run would stop here and ask."
          : "It’s outside the workspace and the allowed folders, and there’s no such folder on this computer."}
      </span>
      <div className="flex flex-wrap items-center gap-2">
        {check.exists && (
          <>
            <button type="button" className={`${small} bg-[var(--primary)] font-medium text-[var(--primary-fg)] hover:bg-[var(--primary-hover)]`} onClick={() => void allow(false)}>
              Only this task
            </button>
            <button type="button" className={`${small} border border-[var(--border)] hover:bg-[var(--card-bg)]`} onClick={() => void allow(true)}>
              Allow everywhere
            </button>
          </>
        )}
        <button type="button" className={`${small} text-[var(--muted)] hover:text-[var(--fg)]`} onClick={onPickAnother}>
          Pick another folder
        </button>
      </div>
      {check.exists && <span className="text-xs text-[var(--muted)]">Only this task lets its runs read and write it. Allow everywhere adds it to Allowed folders.</span>}
      {error && <span className="text-[var(--danger)]">{error}</span>}
    </div>
  );
}

/** Where the folder falls, checked as it is typed or picked. A value worked out from another
 * input or a step is only known as a run goes, so it isn't checked. */
function useReachCheck(taskId: string, value: string, changed: number): ReachCheck | null {
  const [checked, setChecked] = useState<{ key: string; check: ReachCheck | null } | null>(null);
  const key = `${value}\n${changed}`;
  const checkable = value.trim() !== "" && !value.includes("{{");
  useEffect(() => {
    if (!checkable) return;
    let live = true;
    const timer = setTimeout(() => {
      void checkReach(taskId, value).then((result) => live && setChecked({ key, check: "error" in result ? null : result }));
    }, 300);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [taskId, value, key, checkable]);
  return checkable && checked?.key === key ? checked.check : null;
}

/** Closes a menu when a press lands outside it. */
function useClickAway(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const away = (event: MouseEvent) => !ref.current?.contains(event.target as Node) && close();
    window.addEventListener("mousedown", away);
    return () => window.removeEventListener("mousedown", away);
  }, [open, close]);
  return ref;
}

/** A folder input on a saved task: typed or pasted, or picked from what the task reaches, and
 * checked against that reach so a folder outside it can be allowed now. */
export function FolderValue({
  taskId,
  onChanged,
  value,
  onChange,
  label,
  placeholder,
}: {
  taskId: string;
  onChanged: () => void;
  value: string;
  onChange: (value: string | null) => void;
  label: string;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [browsing, setBrowsing] = useState(false);
  const [changed, setChanged] = useState(0);
  const { reach } = useTaskReach(taskId, String(changed));
  const check = useReachCheck(taskId, value, changed);
  const ref = useClickAway(open, () => setOpen(false));
  const pick = (next: string) => {
    onChange(next);
    setOpen(false);
  };
  const allowed = () => {
    setChanged((n) => n + 1);
    onChanged();
  };
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <div
        ref={ref}
        className="relative flex min-w-0 gap-1.5"
        onKeyDown={(event) => {
          // Taken here so the dialog around it, which closes on Escape, stays open.
          if (open && event.key === "Escape") {
            event.stopPropagation();
            setOpen(false);
          }
        }}
      >
        <input
          aria-label={label}
          className={`${controlClass} w-full min-w-0`}
          value={value}
          placeholder={placeholder}
          spellCheck={false}
          onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
        />
        <button
          type="button"
          aria-label={`Choose a folder for ${label}`}
          aria-haspopup="menu"
          aria-expanded={open}
          disabled={!reach}
          className={`${controlClass} flex shrink-0 items-center gap-1 !px-2`}
          onClick={() => setOpen(!open)}
        >
          <FolderIcon className="h-3.5 w-3.5" />
          <ChevronDownIcon className="h-3 w-3 text-[var(--muted)]" />
        </button>
        {open && reach && (
          <FolderMenu
            reach={reach}
            value={value}
            label={`Folders for ${label}`}
            onPick={pick}
            onBrowse={() => {
              setOpen(false);
              setBrowsing(true);
            }}
          />
        )}
      </div>
      {check?.inside && (
        <span className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
          <CheckIcon className="h-3.5 w-3.5 shrink-0" />
          {check.inside === "workspace" ? "In the workspace" : `In ${folderName(check.root ?? "")}, ${WHERE[check.inside]}`}
          {check.writable ? "." : " (read only): a run that saves here stops to ask."}
        </span>
      )}
      {check && check.inside === null && <OutsideCard check={check} taskId={taskId} onAllowed={allowed} onPickAnother={() => setOpen(true)} />}
      {browsing && (
        <DirBrowserModal
          onClose={() => setBrowsing(false)}
          onSelect={(path) => {
            setBrowsing(false);
            onChange(path);
          }}
        />
      )}
    </div>
  );
}
