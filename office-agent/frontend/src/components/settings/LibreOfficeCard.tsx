import { libreOfficeSummary } from "../../lib/useLibreOffice";
import type { LibreOfficeStatus } from "../../types/settings";
import { SettingsSection } from "./SettingRow";

/** Whether a LibreOffice is on this computer. Coscribe works without one; with one it can show
 * Word, Excel and PowerPoint files as pages and check how a document lays out. */
export function LibreOfficeSection({ id, status }: { id: string; status: LibreOfficeStatus | null }) {
  return (
    <div id={id}>
      <SettingsSection
        title="LibreOffice"
        description="A free office program Coscribe can use, when it is there, to draw Word, Excel and PowerPoint files as pages and to check how a document lays out."
      >
        <div className="flex flex-col gap-1 rounded-xl border border-[var(--border)] px-4 py-3">
          <span className="text-[15px] font-medium">{libreOfficeSummary(status)}</span>
          {status?.found && (
            <p className="break-all text-[13px] leading-relaxed text-[var(--muted)]">
              {status.source === "own" ? "Coscribe's own copy" : "Installed on this computer"}: {status.path}
              {status.version === null && " It did not report a version, so it may not start."}
            </p>
          )}
          {status && !status.found && (
            <p className="text-[13px] leading-relaxed text-[var(--muted)]">
              Optional. Without it Coscribe still reads and writes Word, Excel and PowerPoint files; it just can't show them as pages or check their layout.
            </p>
          )}
        </div>
      </SettingsSection>
    </div>
  );
}
