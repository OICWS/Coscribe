import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { chooseFirstWorkspace, getFirstWorkspace } from "../lib/rest";
import { FolderIcon } from "./icons";
import { DirBrowserModal } from "./settings";
import { primaryButtonClass, secondaryButtonClass } from "./settings";

/** The first start asks where Coscribe keeps its work (decision 0048), instead of a hidden folder. */
export function FirstWorkspaceDialog() {
  const [folder, setFolder] = useState<string | null>(null);
  const [browsing, setBrowsing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getFirstWorkspace()
      .then((first) => first.needed && setFolder(first.suggested))
      .catch(() => undefined);
  }, []);

  if (folder === null) return null;
  const choose = async () => {
    setSaving(true);
    const result = await chooseFirstWorkspace(folder);
    setSaving(false);
    if ("error" in result) setError(result.error);
    // Open conversations already know their new folder; a reload shows it everywhere else too.
    else window.location.reload();
  };
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="first-workspace-title"
        className="flex w-[min(520px,100vw-2rem)] flex-col gap-4 rounded-2xl border border-[var(--border)] bg-[var(--panel-bg)] p-6 shadow-[var(--shadow)]"
      >
        <div>
          <h2 id="first-workspace-title" className="text-lg font-semibold">
            Choose a workspace
          </h2>
          <p className="mt-1.5 text-sm leading-relaxed text-[var(--muted)]">
            What Coscribe makes is saved in this folder, and the files you attach go in its .coscribe folder. You can change it later in
            Settings › Workspaces.
          </p>
        </div>
        <div className="flex min-w-0 items-center gap-2 rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
          <FolderIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
          <span className="min-w-0 flex-1 truncate" title={folder}>
            {folder}
          </span>
          <button type="button" className={secondaryButtonClass} onClick={() => setBrowsing(true)}>
            Change…
          </button>
        </div>
        {error && (
          <p role="alert" className="text-[13px] text-[var(--danger)]">
            {error}
          </p>
        )}
        <div className="flex justify-end">
          <button type="button" className={primaryButtonClass} disabled={saving} onClick={() => void choose()}>
            Use this folder
          </button>
        </div>
      </div>
      {browsing && (
        <DirBrowserModal
          onClose={() => setBrowsing(false)}
          onSelect={(path) => {
            setBrowsing(false);
            setError(null);
            setFolder(path);
          }}
        />
      )}
    </div>,
    document.body,
  );
}
