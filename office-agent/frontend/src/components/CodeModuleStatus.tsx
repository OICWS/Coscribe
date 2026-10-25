import type { useCodeStatus } from "../lib/useCodeStatus";

function megabytes(bytes: number): string {
  return `${Math.round(bytes / 1_000_000)} MB`;
}

/** Whether Codex is downloaded, with Download or Remove, and any older version still on disk
 * (Remove takes every version). */
export function CodeDownload({
  code,
  compact = false,
  folder,
}: {
  code: ReturnType<typeof useCodeStatus>;
  compact?: boolean;
  /** Where Codex's versions live, shown so the person can find them. */
  folder?: string;
}) {
  const { status, error, preparing } = code;
  if (!status) return null;
  const size = status.size === null ? null : megabytes(status.size);
  let text: string;
  if (preparing) {
    text =
      status.progress === null
        ? "Getting the code module ready..."
        : `Downloading Codex ${status.version}... ${Math.round(status.progress * 100)}%`;
  } else if (status.installed) {
    text = `Codex ${status.version} is downloaded${size ? ` (${size} on disk)` : ""}.`;
  } else if (status.size === null) {
    text = "The code module has no Codex build for this computer.";
  } else {
    text = `Codex ${status.version} downloads the first time it's used, ${size} on disk.`;
  }
  const older = status.older ?? [];
  // A pin moved past what is on disk: coscribe uses only the version it was tested with.
  const updating = !status.installed && status.size !== null && older.length > 0;
  if (updating && !preparing) {
    text = `This coscribe uses Codex ${status.version}, ${size} on disk; the one downloaded is older.`;
  }
  let action: string | null = null;
  if (updating) action = `Update to ${status.version}`;
  else if (!status.installed && status.size !== null) action = "Download now";
  else if (status.installed && !compact) action = "Remove";
  const olderSize = older.reduce((sum, old) => sum + old.size, 0);
  const olderText =
    older.length === 0
      ? null
      : `An older Codex (${older.map((old) => old.version).join(", ")}) is still on disk, ${megabytes(olderSize)}${
          older.some((old) => old.sandbox)
            ? ": the command sandbox was set up with it, so removing it turns the sandbox off until it is set up again"
            : ""
        }.`;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-3">
        <span className="min-w-0 flex-1 text-sm text-[var(--muted)]">{text}</span>
        {action && (
          <button
            type="button"
            disabled={preparing}
            className="shrink-0 rounded-md border border-[var(--border)] px-3 py-1 text-sm hover:bg-[var(--card-bg)] disabled:opacity-50"
            onClick={status.installed ? code.remove : code.install}
          >
            {action}
          </button>
        )}
      </div>
      {folder && !compact && (
        <span className="text-[13px] text-[var(--muted)]">
          Kept in <span className="select-all font-mono text-xs">{folder}</span>
        </span>
      )}
      {olderText && !compact && (
        <div className="flex items-center gap-3">
          <span className="min-w-0 flex-1 text-sm text-[var(--muted)]">{olderText}</span>
          {!status.installed && (
            <button
              type="button"
              disabled={preparing}
              className="shrink-0 rounded-md border border-[var(--border)] px-3 py-1 text-sm hover:bg-[var(--card-bg)] disabled:opacity-50"
              onClick={code.remove}
            >
              Remove
            </button>
          )}
        </div>
      )}
      {preparing && status.progress !== null && (
        <div className="h-1 overflow-hidden rounded-full bg-[var(--border)]">
          <div className="h-full bg-[var(--primary)]" style={{ width: `${Math.round(status.progress * 100)}%` }} />
        </div>
      )}
      {error && <span className="text-sm text-[var(--danger)]">{error}</span>}
    </div>
  );
}
