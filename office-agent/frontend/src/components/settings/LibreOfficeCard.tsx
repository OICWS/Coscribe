import { libreOfficeSummary, type useLibreOffice } from "../../lib/useLibreOffice";
import type { LibreOfficeStatus } from "../../types/settings";
import { secondaryButtonClass, SettingsSection } from "./SettingRow";

const STEPS: Record<string, string> = {
  download: "Downloading",
  unpack: "Unpacking",
  trim: "Removing what Coscribe doesn't use",
  check: "Checking that it converts a file",
};

function megabytes(bytes: number): string {
  return `${Math.round(bytes / 1_000_000)} MB`;
}

function Body({ status, error, download, remove }: { status: LibreOfficeStatus } & Omit<ReturnType<typeof useLibreOffice>, "status">) {
  const { offer } = status;
  if (status.working) {
    const percent = status.step === "download" && status.total > 0 ? Math.round((status.done / status.total) * 100) : null;
    return (
      <div className="flex flex-col gap-2">
        <span className="text-[13px] text-[var(--muted)]">
          {STEPS[status.step] ?? "Working"}
          {percent === null ? "…" : `… ${percent}%`} This takes a few minutes.
        </span>
        {percent !== null && (
          <div className="h-1 overflow-hidden rounded-full bg-[var(--border)]">
            <div className="h-full bg-[var(--primary)]" style={{ width: `${percent}%` }} />
          </div>
        )}
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {status.found && (
        <p className="break-all text-[13px] leading-relaxed text-[var(--muted)]">
          {status.source === "own" ? "Coscribe's own copy" : "Installed on this computer"}: {status.path}
          {status.version === null && " It did not report a version, so it may not start."}
        </p>
      )}
      {!status.found && (
        <p className="text-[13px] leading-relaxed text-[var(--muted)]">
          {offer
            ? `Optional. Without it Coscribe still reads and writes Word, Excel and PowerPoint files; it just can't show them as pages or check their layout. Downloading LibreOffice ${offer.version} is ${megabytes(offer.download_bytes)} from The Document Foundation, about ${megabytes(offer.installed_bytes)} on disk afterwards, and needs about 2.2 GB free while it installs. It is unpacked, not installed, so it needs no administrator rights and leaves your own LibreOffice settings alone.`
            : "Optional. Without it Coscribe still reads and writes Word, Excel and PowerPoint files; it just can't show them as pages or check their layout. It can be downloaded here on 64-bit Windows only."}
        </p>
      )}
      <div className="flex items-center gap-3">
        {!status.found && offer && (
          <button type="button" className={secondaryButtonClass} onClick={() => void download()}>
            Download LibreOffice
          </button>
        )}
        {status.found && status.source === "own" && (
          <button type="button" className={secondaryButtonClass} onClick={() => void remove()}>
            Remove
          </button>
        )}
      </div>
      {(error || status.problem) && <span className="text-sm text-[var(--danger)]">{error ?? status.problem}</span>}
    </div>
  );
}

/** Whether a LibreOffice is on this computer, with a button to download Coscribe's own. Coscribe
 * works without one; with one it can show Word, Excel and PowerPoint files as pages and check how a
 * document lays out. */
export function LibreOfficeSection({ id, libreOffice }: { id: string; libreOffice: ReturnType<typeof useLibreOffice> }) {
  const { status, ...actions } = libreOffice;
  return (
    <div id={id}>
      <SettingsSection
        title="LibreOffice"
        description="A free office program Coscribe can use, when it is there, to draw Word, Excel and PowerPoint files as pages and to check how a document lays out."
      >
        <div className="flex flex-col gap-1 rounded-xl border border-[var(--border)] px-4 py-3">
          <span className="text-[15px] font-medium">{libreOfficeSummary(status)}</span>
          {status && <Body status={status} {...actions} />}
        </div>
      </SettingsSection>
    </div>
  );
}
