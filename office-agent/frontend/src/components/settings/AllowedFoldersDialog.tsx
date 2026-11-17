import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { browseDirs } from "../../lib/rest";
import { folderName } from "../../lib/recentFolders";
import { CloseIcon, PlusIcon } from "../icons";
import { SelectMenu } from "../SelectMenu";
import { DirBrowserModal } from "./DirBrowserModal";
import { DIR_PERMISSION_OPTIONS, type DirEntry, type DirPermission } from "./fields";
import { primaryButtonClass, secondaryButtonClass } from "./SettingRow";

/** The folders that can't be opened now: a drive that is unplugged, a share that is offline. */
function useMissingFolders(paths: string[]): Set<string> {
  const [missing, setMissing] = useState<Set<string>>(new Set());
  const key = paths.join("\n");
  useEffect(() => {
    let current = true;
    const list = key ? key.split("\n") : [];
    void Promise.all(list.map((path) => browseDirs(path).then((result) => ("error" in result ? path : null), () => null))).then((found) => {
      if (current) setMissing(new Set(found.filter((path): path is string => path !== null)));
    });
    return () => {
      current = false;
    };
  }, [key]);
  return missing;
}

const cell = "border-b border-[var(--border)] py-2 align-middle";

/** Each folder with its access, or why it can't be used now. */
function FolderTable({ entries, onChange }: { entries: DirEntry[]; onChange: (entries: DirEntry[]) => void }) {
  const missing = useMissingFolders(entries.map((entry) => entry.path));
  const setPermission = (path: string, permission: DirPermission) => onChange(entries.map((e) => (e.path === path ? { ...e, permission } : e)));
  return (
    <div className="min-h-0 overflow-y-auto">
      <table className="w-full table-fixed border-collapse text-[13px]">
        <thead>
          <tr className="text-left text-[var(--muted)]">
            <th className={`${cell} w-[26%] py-1.5 font-normal`}>Folder</th>
            <th className={`${cell} py-1.5 font-normal`}>Location</th>
            <th className={`${cell} w-[196px] py-1.5 font-normal`}>Access</th>
            <th className={`${cell} w-[84px] py-1.5`}>
              <span className="sr-only">Remove</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.path} className="[&:last-child>td]:border-b-0">
              <td className={`${cell} truncate pr-3 text-sm`}>{folderName(entry.path)}</td>
              <td className={`${cell} truncate pr-3 text-[var(--muted)]`} title={entry.path}>
                {entry.path}
              </td>
              {missing.has(entry.path) ? (
                <td className={`${cell} pr-3 text-[var(--muted)]`}>Can’t be found right now. Used again if it comes back.</td>
              ) : (
                <td className={`${cell} pr-3`}>
                  <SelectMenu
                    variant="field"
                    className="w-[180px]"
                    triggerClassName="h-8 text-[13px]"
                    ariaLabel={`Access to ${entry.path}`}
                    value={entry.permission}
                    options={DIR_PERMISSION_OPTIONS}
                    onChange={(value) => setPermission(entry.path, value)}
                  />
                </td>
              )}
              <td className={`${cell} text-right`}>
                <button
                  type="button"
                  aria-label={`Remove ${entry.path}`}
                  className={`${secondaryButtonClass} !h-8 !px-2.5 text-[13px]`}
                  onClick={() => onChange(entries.filter((e) => e.path !== entry.path))}
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Settings' Allowed folders, managed in a dialog the way Settings › Environments links to it. */
export function AllowedFoldersDialog({ entries, onChange, onClose }: { entries: DirEntry[]; onChange: (entries: DirEntry[]) => void; onClose: () => void }) {
  const [browsing, setBrowsing] = useState(false);

  useEffect(() => {
    if (browsing) return;
    const onKeyDown = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [browsing, onClose]);

  const add = (path: string) => {
    if (!entries.some((entry) => entry.path === path)) onChange([...entries, { path, permission: "read" }]);
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="allowed-folders-title"
        className="flex max-h-full w-[min(680px,100vw-2rem)] flex-col gap-4 rounded-2xl border border-[var(--border)] bg-[var(--panel-bg)] p-6 shadow-[var(--shadow)]"
      >
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <h2 id="allowed-folders-title" className="text-lg font-semibold">
              Allowed folders
            </h2>
            <p className="mt-1.5 text-sm leading-relaxed text-[var(--muted)]">
              Every environment can use these folders and the folders inside them. When a chat needs another folder, it asks first, and Allow adds
              it here. Remove one and Coscribe asks again next time.
            </p>
          </div>
          <button
            type="button"
            aria-label="Close"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
            onClick={onClose}
          >
            <CloseIcon className="h-4 w-4" />
          </button>
        </div>

        {entries.length === 0 ? (
          <p className="py-2 text-sm text-[var(--muted)]">No allowed folders yet. Add one, or allow one when a chat asks.</p>
        ) : (
          <FolderTable entries={entries} onChange={onChange} />
        )}

        <p className="text-xs leading-relaxed text-[var(--muted)]">
          Deleting, moving or renaming files needs read, write and delete; deleted files go to the Recycle Bin. Scripts read nothing outside
          these folders.
        </p>

        <div className="flex items-center gap-2">
          <button type="button" className={`${secondaryButtonClass} flex items-center gap-1.5`} onClick={() => setBrowsing(true)}>
            <PlusIcon className="h-4 w-4" />
            Add folder
          </button>
          <button type="button" className={`${primaryButtonClass} ml-auto`} onClick={onClose}>
            Done
          </button>
        </div>
      </div>
      {browsing && (
        <DirBrowserModal
          onClose={() => setBrowsing(false)}
          onSelect={(path) => {
            add(path);
            setBrowsing(false);
          }}
        />
      )}
    </div>,
    document.body,
  );
}
