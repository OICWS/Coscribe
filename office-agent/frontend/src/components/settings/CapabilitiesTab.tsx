import { useEffect, useState } from "react";
import {
  getCapabilities,
  getCapabilityFolders,
  getNodeEnvPackages,
  getScriptEnvPackages,
  installNodeEnvPackage,
  installScriptEnvPackage,
  removeNodeEnvPackage,
  removeScriptEnvPackage,
  setCapability,
} from "../../lib/rest";
import { useCodeStatus } from "../../lib/useCodeStatus";
import type { Capabilities, CapabilityFolders, CommandSandbox, CodeStatus } from "../../types/settings";
import { ConfirmDialog } from "../ConfirmDialog";
import { ToggleSwitch } from "../ToggleSwitch";
import { CodeTab } from "./CodeTab";
import { CommandModes, useCommandSandbox } from "./CommandModes";
import { CODE_MODULE_ENABLED_KEY } from "./fields";
import { PackageListSection } from "./PackageListSection";
import { PythonInterpreterSection } from "./PythonInterpreterSection";
import { ScriptIsolationCard } from "./ScriptIsolationCard";
import { SettingRow, SettingRows, SettingsSection } from "./SettingRow";

function useCapabilities(active: boolean) {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (active) getCapabilities().then(setCapabilities, () => setError("Could not read the capabilities."));
  }, [active]);
  const set = (name: keyof Capabilities, on: boolean) => {
    setError(null);
    setCapability(name, on).then(setCapabilities, (err: unknown) =>
      setError(err instanceof Error ? err.message : "Could not save."),
    );
  };
  return { capabilities, error, set };
}

function useFolders(active: boolean) {
  const [folders, setFolders] = useState<CapabilityFolders | null>(null);
  useEffect(() => {
    if (active) getCapabilityFolders().then(setFolders, () => setFolders(null));
  }, [active]);
  return folders;
}

const SECTIONS = { scripts: "capability-scripts", commands: "capability-commands", code: "capability-code" } as const;

function commandsSummary(capabilities: Capabilities, sandbox: CommandSandbox | null): string {
  if (!capabilities.commands) return "Off";
  if (sandbox?.state === "working") return "On · setting up the sandbox…";
  if (sandbox?.state === "ready") return sandbox.mode === "unelevated" ? "On · basic sandbox" : "On · full sandbox";
  if (capabilities.commands_without_sandbox) return "On · without a sandbox";
  return "On, but refused until a sandbox is set up";
}

function codeSummary(status: CodeStatus | null, codeOn: boolean): string {
  const codex = status?.installed ? `Codex ${status.version} downloaded` : "Codex not downloaded";
  return `${codeOn ? "On" : "Off"} · ${codex}`;
}

/** One line per capability, what it is set to now; each jumps to its section. */
function Overview({ rows }: { rows: { label: string; what: string; now: string; section?: string }[] }) {
  return (
    <SettingsSection
      title="What Coscribe can run on this computer"
      description="From the safest to the most powerful. A conversation's environment or permission mode can only narrow what is allowed here."
    >
      <div className="mt-2 flex flex-col divide-y divide-[var(--border)] rounded-xl border border-[var(--border)]">
        {rows.map((row) => {
          const body = (
            <>
              <div className="flex min-w-0 flex-col">
                <span className="text-[15px] text-[var(--fg)]">{row.label}</span>
                <span className="text-[13px] text-[var(--muted)]">{row.what}</span>
              </div>
              <span className="shrink-0 text-right text-[13px] text-[var(--fg)]">{row.now}</span>
            </>
          );
          const className = "flex w-full items-center justify-between gap-6 px-4 py-2.5 text-left";
          return row.section ? (
            <button
              key={row.label}
              type="button"
              className={`${className} hover:bg-[var(--card-bg)]`}
              onClick={() => document.getElementById(row.section ?? "")?.scrollIntoView({ behavior: "smooth" })}
            >
              {body}
            </button>
          ) : (
            <div key={row.label} className={className}>
              {body}
            </div>
          );
        })}
      </div>
    </SettingsSection>
  );
}

function ScriptsSection({
  active,
  on,
  onToggle,
  folders,
}: {
  active: boolean;
  on: boolean;
  onToggle: () => void;
  folders: CapabilityFolders | null;
}) {
  const [showSetup, setShowSetup] = useState(false);
  return (
    <div id={SECTIONS.scripts}>
      <SettingsSection
        title="Scripts"
        description="When a task is too big or too specific for the built-in tools, Coscribe writes a Python or Node.js script and runs it after you approve it. On Windows a script runs isolated: it can use only the folders of its environment, can't delete or rename files there, and can't reach the rest of this computer."
      >
        <SettingRows>
          <SettingRow
            label="Run scripts"
            description="Off, scripts are refused and Coscribe uses its built-in tools only."
            control={<ToggleSwitch label="Run scripts" on={on} onClick={onToggle} />}
          />
        </SettingRows>
        <div className="flex flex-col gap-4 pt-2">
          <ScriptIsolationCard active={active} />
          <button
            type="button"
            aria-expanded={showSetup}
            className="self-start text-sm text-[var(--accent)] hover:underline"
            onClick={() => setShowSetup(!showSetup)}
          >
            {showSetup ? "Hide" : "Show"} Python and packages
          </button>
          {showSetup && (
            <div className="flex flex-col gap-6 border-l-2 border-[var(--border)] pl-4">
              <PythonInterpreterSection active={active} />
              <PackageListSection
                title="Python packages"
                description={`Libraries Python scripts can use. They go in a virtual environment made from the Python above; choosing another Python makes it again, empty.${
                  folders ? ` Kept in ${folders.python_packages}.` : ""
                }`}
                placeholder="Library name, e.g. numpy"
                emptyStateText="None yet -- scripts can use Python's standard library only."
                active={active}
                getPackages={getScriptEnvPackages}
                installPackage={installScriptEnvPackage}
                removePackage={removeScriptEnvPackage}
              />
              <PackageListSection
                title="Node.js packages"
                description={`Libraries Node.js scripts can use, besides pptxgenjs. Node.js scripts need Node.js installed on this computer.${
                  folders ? ` Kept in ${folders.node_packages}.` : ""
                }`}
                placeholder="Package name, e.g. sharp"
                emptyStateText="None added beyond pptxgenjs."
                active={active}
                getPackages={getNodeEnvPackages}
                installPackage={installNodeEnvPackage}
                removePackage={removeNodeEnvPackage}
              />
            </div>
          )}
        </div>
      </SettingsSection>
    </div>
  );
}

// Turning commands on, and then letting them run outside the sandbox, are two separate risks,
// each confirmed once (decision 0022).
const CONFIRMATIONS = {
  commands: {
    title: "Turn on commands?",
    description:
      "In a command sandbox a command can write only its environment's folders. Without one, a command runs as you: one you approve can change or delete any of your files.",
    confirmLabel: "Turn on",
  },
  commands_without_sandbox: {
    title: "Run commands without the sandbox?",
    description:
      "A command would run as you, with nothing to hold it to its folders: one you approve can change or delete any of your files and reach the internet. Coscribe asks before each command, in every mode, and never lets Auto mode approve one.",
    confirmLabel: "Allow",
  },
} as const;

interface CapabilitiesTabProps {
  active: boolean;
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
}

/** Everything coscribe may run on this computer, in one place (#588): an overview, then each
 * capability from the safest to the most powerful. An environment or a mode can only narrow what
 * is on here. */
export function CapabilitiesTab({ active, values, onChange }: CapabilitiesTabProps) {
  const { capabilities, error, set } = useCapabilities(active);
  const sandbox = useCommandSandbox(active);
  const code = useCodeStatus();
  const folders = useFolders(active);
  const [confirm, setConfirm] = useState<keyof typeof CONFIRMATIONS | null>(null);
  if (capabilities === null) {
    return <p className="text-sm text-[var(--muted)]">{error ?? "Loading…"}</p>;
  }
  const codeOn = values[CODE_MODULE_ENABLED_KEY] === "true";
  return (
    <div className="flex flex-col gap-10">
      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
      <Overview
        rows={[
          {
            label: "Built-in tools",
            what: "Files, Word, Excel, PowerPoint, PDF, the web and connectors, in the environment's folders",
            now: "Always on",
          },
          {
            label: "Scripts",
            what: "Python or Node.js that Coscribe writes, isolated to the environment's folders",
            now: capabilities.scripts ? "On" : "Off",
            section: SECTIONS.scripts,
          },
          {
            label: "Commands",
            what: "cmd or PowerShell lines: git, build tools, installers",
            now: commandsSummary(capabilities, sandbox.sandbox),
            section: SECTIONS.commands,
          },
          {
            label: "Code module",
            what: "Codex writes and fixes code for a chat",
            now: codeSummary(code.status, codeOn),
            section: SECTIONS.code,
          },
        ]}
      />
      <ScriptsSection
        active={active}
        on={capabilities.scripts}
        onToggle={() => set("scripts", !capabilities.scripts)}
        folders={folders}
      />
      <div id={SECTIONS.commands}>
        <SettingsSection
          title="Commands"
          description="Command lines in cmd or PowerShell, for what a script can't do: build tools, git, installers. Choose below how they are held."
        >
          <SettingRows>
            <SettingRow
              label="Run commands"
              description="Off by default. Turning it on is recorded in the audit log."
              control={
                <ToggleSwitch
                  label="Run commands"
                  on={capabilities.commands}
                  onClick={() => (capabilities.commands ? set("commands", false) : setConfirm("commands"))}
                />
              }
            />
          </SettingRows>
          <CommandModes
            control={sandbox}
            withoutSandbox={capabilities.commands_without_sandbox}
            onToggleWithoutSandbox={() =>
              capabilities.commands_without_sandbox
                ? set("commands_without_sandbox", false)
                : setConfirm("commands_without_sandbox")
            }
            hidePrivate={capabilities.commands_hide_private_folders}
            onToggleHidePrivate={() => set("commands_hide_private_folders", !capabilities.commands_hide_private_folders)}
          />
        </SettingsSection>
      </div>
      <div id={SECTIONS.code}>
        <CodeTab values={values} onChange={onChange} code={code} codexFolder={folders?.codex} />
      </div>
      {confirm && (
        <ConfirmDialog
          {...CONFIRMATIONS[confirm]}
          onCancel={() => setConfirm(null)}
          onConfirm={() => {
            setConfirm(null);
            set(confirm, true);
          }}
        />
      )}
    </div>
  );
}
