import { useEffect, useState } from "react";
import {
  getCapabilityFolders,
  getNodeEnvPackages,
  getScriptEnvPackages,
  installNodeEnvPackage,
  installScriptEnvPackage,
  removeNodeEnvPackage,
  removeScriptEnvPackage,
} from "../../lib/rest";
import type { useCodeStatus } from "../../lib/useCodeStatus";
import { useLibreOffice } from "../../lib/useLibreOffice";
import type { CapabilityFolders } from "../../types/settings";
import { PackageListSection } from "./PackageListSection";
import { PythonInterpreterSection } from "./PythonInterpreterSection";
import { secondaryButtonClass, SettingRow, SettingRows, SettingsSection } from "./SettingRow";

function megabytes(bytes: number): string {
  return `${Math.round(bytes / 1_000_000)} MB`;
}

const pathClass = "mt-1 block break-all font-mono text-xs";
const problemClass = "mt-1 block text-[var(--danger)]";

function LibreOfficeRow({ active }: { active: boolean }) {
  const libreOffice = useLibreOffice(active);
  const office = libreOffice.status;
  let text = "Checking…";
  if (office) {
    if (office.working)
      text = `Getting it ready${office.step === "download" && office.total > 0 ? `… ${Math.round((office.done / office.total) * 100)}%` : "…"} This takes a few minutes.`;
    else if (office.found) text = `LibreOffice ${office.version ?? ""} ${office.source === "system" ? "is installed on this computer" : "is downloaded"}.`;
    else if (office.offer) text = `Not downloaded. ${megabytes(office.offer.download_bytes)} to download, ${megabytes(office.offer.installed_bytes)} on disk.`;
    else text = "Not found. It can be downloaded here on 64-bit Windows only.";
  }
  let control = null;
  if (office && !office.found && office.offer) {
    control = (
      <button type="button" className={secondaryButtonClass} disabled={office.working} onClick={() => void libreOffice.download()}>
        Download
      </button>
    );
  } else if (office?.found && office.source === "own") {
    control = (
      <button type="button" className={secondaryButtonClass} onClick={() => void libreOffice.remove()}>
        Remove
      </button>
    );
  }
  return (
    <SettingRow
      label="LibreOffice"
      description={
        <>
          Lets Coscribe show Word, Excel and PowerPoint files as pages and check their layout. {text}
          {office?.found && office.path && <span className={pathClass}>{office.path}</span>}
          {(libreOffice.error || office?.problem) && <span className={problemClass}>{libreOffice.error ?? office?.problem}</span>}
        </>
      }
      control={control}
    />
  );
}

/** Codex is downloaded, updated and removed only from here: a pin that moved past the version
 * on disk offers an update, and never fetches it unasked. */
function CodexRow({ code, folder, runsSandbox }: { code: ReturnType<typeof useCodeStatus>; folder?: string; runsSandbox: boolean }) {
  const status = code.status;
  const older = status?.older ?? [];
  const update = Boolean(status && !status.installed && status.size !== null && older.length > 0);
  const size = status?.size == null ? "" : megabytes(status.size);
  let text = "Checking…";
  if (status) {
    if (code.preparing) text = status.progress === null ? "Getting it ready…" : `Downloading… ${Math.round(status.progress * 100)}%`;
    else if (status.installed)
      text = `Codex ${status.version} is downloaded${size ? `, ${size} on disk` : ""}.${older.length > 0 ? " An older version is still on disk; Remove takes both." : ""}`;
    else if (status.size === null) text = "No Codex build for this computer.";
    else if (update) text = `Codex ${older.map((old) => old.version).join(", ")} is downloaded; this Coscribe uses ${status.version}, ${size} on disk.`;
    else text = `Not downloaded. ${size} on disk.`;
  }
  return (
    <SettingRow
      label="Codex"
      description={
        <>
          OpenAI's coding agent. Code runs on it{runsSandbox ? ", and so does the command sandbox" : ""}. {text}
          {status?.installed && folder && <span className={pathClass}>{folder}</span>}
          {code.error && <span className={problemClass}>{code.error}</span>}
        </>
      }
      control={
        status && (status.installed || status.size !== null) ? (
          <button type="button" className={secondaryButtonClass} disabled={code.preparing} onClick={() => void (status.installed ? code.remove() : code.install())}>
            {status.installed ? "Remove" : update ? `Update to ${status.version}` : "Download"}
          </button>
        ) : null
      }
    />
  );
}

function Packages({ active, folders }: { active: boolean; folders: CapabilityFolders | null }) {
  return (
    <div className="sub-rows pb-4">
      <PackageListSection
        title="Python packages"
        description={folders ? `Kept in ${folders.python_packages}.` : ""}
        placeholder="Library name, e.g. numpy"
        emptyStateText="None yet -- scripts can use Python's standard library only."
        active={active}
        getPackages={getScriptEnvPackages}
        installPackage={installScriptEnvPackage}
        removePackage={removeScriptEnvPackage}
      />
      <PackageListSection
        title="Node.js packages"
        description={`Node.js scripts need Node.js installed on this computer.${folders ? ` Kept in ${folders.node_packages}.` : ""}`}
        placeholder="Package name, e.g. sharp"
        emptyStateText="None added beyond pptxgenjs."
        active={active}
        getPackages={getNodeEnvPackages}
        installPackage={installNodeEnvPackage}
        removePackage={removeNodeEnvPackage}
      />
    </div>
  );
}

interface AdvancedSectionProps {
  active: boolean;
  code: ReturnType<typeof useCodeStatus>;
  /** False where the sandbox ships with the app, so Codex is only for Code. */
  codexRunsSandbox: boolean;
}

/** What few people touch: which Python and packages scripts get, and the two large optional
 * downloads, each fetched, updated and removed only when the person asks. */
export function AdvancedSection({ active, code, codexRunsSandbox }: AdvancedSectionProps) {
  const [open, setOpen] = useState<"python" | "packages" | null>(null);
  const [folders, setFolders] = useState<CapabilityFolders | null>(null);
  useEffect(() => {
    if (active) getCapabilityFolders().then(setFolders, () => setFolders(null));
  }, [active]);
  const expander = (name: "python" | "packages", closed: string) => (
    <button type="button" className={secondaryButtonClass} aria-expanded={open === name} onClick={() => setOpen(open === name ? null : name)}>
      {open === name ? "Done" : closed}
    </button>
  );
  return (
    <SettingsSection title="Advanced" description="What scripts run on, and optional downloads. You choose when to download, update or remove each one.">
      <SettingRows>
        <SettingRow
          label="Python for scripts"
          description="Which Python runs scripts. Coscribe picks one that works; choose another, or download Coscribe's own, if scripts can't start."
          control={expander("python", "Choose")}
        />
        {open === "python" && (
          <div className="sub-rows pb-4">
            <PythonInterpreterSection active={active} />
          </div>
        )}
        <SettingRow
          label="Packages for scripts"
          description="Python and Node.js libraries that scripts can use, beyond the ones that come with Coscribe."
          control={expander("packages", "Manage")}
        />
        {open === "packages" && <Packages active={active} folders={folders} />}
        <LibreOfficeRow active={active} />
        <CodexRow code={code} folder={folders?.codex} runsSandbox={codexRunsSandbox} />
      </SettingRows>
    </SettingsSection>
  );
}
