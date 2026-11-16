import { useEffect, useState } from "react";
import { getCapabilities, getScriptIsolation, retestScriptIsolation, setCapability } from "../../lib/rest";
import { isElectron } from "../../lib/electron";
import { useCodePermissions } from "../../lib/useCodePermissions";
import { useCodeStatus } from "../../lib/useCodeStatus";
import type { Capabilities, ScriptIsolation } from "../../types/settings";
import { AllowedSitesDialog } from "../AllowedSitesDialog";
import { CHECK_WORDS } from "../environment/checkWords";
import { ToggleSwitch } from "../ToggleSwitch";
import { AdvancedSection } from "./AdvancedSection";
import { CommandRows } from "./CommandRows";
import { ConfiguredModelSelect } from "./ConfiguredModelSelect";
import { CODE_MODEL_KEY, CODE_MODULE_ENABLED_KEY } from "./fields";
import { secondaryButtonClass, SettingRow, SettingRows, SettingsSection, SubRows } from "./SettingRow";
import { useCommandSandbox } from "./useCommandSandbox";

function useCapabilities(active: boolean) {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (active) getCapabilities().then(setCapabilities, () => setError("Could not read the capabilities."));
  }, [active]);
  const set = (name: keyof Capabilities, on: boolean) => {
    setError(null);
    setCapability(name, on).then(setCapabilities, (err: unknown) => setError(err instanceof Error ? err.message : "Could not save."));
  };
  return { capabilities, error, set };
}

/** The isolation check, run by Coscribe itself: nothing shows while it holds, one line with a
 * way to try again when it doesn't. */
function useScriptIsolation(active: boolean) {
  const [status, setStatus] = useState<ScriptIsolation | null>(null);
  const [checking, setChecking] = useState(false);
  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    getScriptIsolation()
      .then((result) => (result.state === "untested" ? retestScriptIsolation() : result))
      .then((result) => !cancelled && setStatus(result))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [active]);
  const retry = () => {
    setChecking(true);
    retestScriptIsolation()
      .then(setStatus, () => undefined)
      .finally(() => setChecking(false));
  };
  return { status, checking, retry };
}

function isolationProblem(status: ScriptIsolation | null): string | null {
  if (status?.state === "setup_failed") return `Scripts have no Python to run with yet. ${status.detail}`;
  if (status?.state === "failed")
    return `Scripts are off here because they can't be kept to their folders on this computer (${(
      CHECK_WORDS[status.failed] ?? status.failed
    ).toLowerCase()}). Security software or a company policy can cause this. A conversation can still allow them from its environment.`;
  return null;
}

function ScriptsRow({ active, on, toggle }: { active: boolean; on: boolean; toggle: () => void }) {
  const isolation = useScriptIsolation(active);
  const problem = isolationProblem(isolation.status);
  return (
    <SettingRow
      label="Run scripts"
      description={
        <>
          For work too big for the built-in tools, Coscribe writes a Python or Node.js script and runs it after you approve it, kept to the folders of its environment.
          {on && problem && (
            <span className="mt-1 block text-[var(--danger)]">
              {isolation.checking ? "Checking again…" : problem}{" "}
              {!isolation.checking && (
                <button type="button" className="underline" onClick={isolation.retry}>
                  Retry
                </button>
              )}
            </span>
          )}
        </>
      }
      control={<ToggleSwitch label="Run scripts" on={on} onClick={toggle} />}
    />
  );
}

interface CodeRowsProps {
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  code: ReturnType<typeof useCodeStatus>;
}

/** Handing work to Code is only a switch: Codex itself is a download the person starts, under Advanced. */
function CodeRows({ values, onChange, code }: CodeRowsProps) {
  const approvals = useCodePermissions();
  const on = values[CODE_MODULE_ENABLED_KEY] === "true";
  const problem = code.error ?? code.status?.model_problem;
  return (
    <>
      <SettingRow
        label="Chats can hand tasks to Code"
        description={
          <>
            A chat passes work that needs real code, such as processing data across many files, to a coding agent and gets its report back.
            {code.status && !code.status.installed && " Needs Codex, under Advanced below."}
            {on && problem && <span className="mt-1 block text-[var(--danger)]">{problem}</span>}
          </>
        }
        control={<ToggleSwitch label="Chats can hand tasks to Code" on={on} onClick={() => onChange(CODE_MODULE_ENABLED_KEY, on ? "false" : "true")} />}
      />
      {on && (
        <SubRows>
          <SettingRow
            label="Model for code"
            description="What the coding agent runs on. Left as the chat's model, it works with an OpenAI model or a provider that serves the Responses API; with Claude or Gemini in the chat, pick one here."
            control={<ConfiguredModelSelect ariaLabel="Model for code" value={values[CODE_MODEL_KEY] ?? ""} onChange={(v) => onChange(CODE_MODEL_KEY, v)} />}
          />
          {approvals.permissions && (
            <SettingRow
              label="Change files without asking"
              description="Off, it asks before each file change."
              control={
                <ToggleSwitch
                  label="Change files without asking"
                  on={approvals.permissions.apply_code_change === "allow"}
                  onClick={() => approvals.set("apply_code_change", approvals.permissions?.apply_code_change === "allow" ? "ask" : "allow")}
                />
              }
            />
          )}
        </SubRows>
      )}
    </>
  );
}

interface CapabilitiesTabProps {
  active: boolean;
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  onOpenEnvironments: () => void;
}

/** Everything Coscribe may do on this computer, one switch each (#588). Coscribe sets up what a
 * switch needs (a sandbox, a check) itself; a large download is the person's to start, under
 * Advanced. An environment or a mode can only narrow what is on here. */
export function CapabilitiesTab({ active, values, onChange, onOpenEnvironments }: CapabilitiesTabProps) {
  const [sitesOpen, setSitesOpen] = useState(false);
  const { capabilities, error, set } = useCapabilities(active);
  const sandbox = useCommandSandbox(active);
  const code = useCodeStatus();

  if (capabilities === null) {
    return <p className="text-sm text-[var(--muted)]">{error ?? "Loading…"}</p>;
  }
  return (
    <div className="flex flex-col gap-10">
      <SettingsSection title="Capabilities">
        {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
        <SettingRows>
          <SettingRow
            label="Create and edit files"
            description="Coscribe writes and changes files in the folders of its environment: Word, Excel, PowerPoint, PDF and text. Off, it only reads them and answers in the conversation; a script or command you approve can still write."
            control={<ToggleSwitch label="Create and edit files" on={capabilities.files} onClick={() => set("files", !capabilities.files)} />}
          />
          {capabilities.files && (
            <SubRows>
              <SettingRow
                label="Artifacts"
                description="Docs, designs and dashboards that open beside the conversation. Off, Coscribe answers in the conversation or writes an Office file; the ones already made still open."
                control={<ToggleSwitch label="Artifacts" on={capabilities.artifacts} onClick={() => set("artifacts", !capabilities.artifacts)} />}
              />
            </SubRows>
          )}
          <ScriptsRow active={active} on={capabilities.scripts} toggle={() => set("scripts", !capabilities.scripts)} />
          <CommandRows capabilities={capabilities} set={set} control={sandbox} onOpenEnvironments={onOpenEnvironments} />
          {isElectron() && (
            <SettingRow
              label="Allowed sites"
              description="Sites where Coscribe can use its browser without asking you first."
              control={
                <button type="button" className={secondaryButtonClass} onClick={() => setSitesOpen(true)}>
                  Manage
                </button>
              }
            />
          )}
          <CodeRows values={values} onChange={onChange} code={code} />
        </SettingRows>
        {sitesOpen && <AllowedSitesDialog onClose={() => setSitesOpen(false)} />}
      </SettingsSection>
      <AdvancedSection active={active} code={code} codexRunsSandbox={sandbox.sandbox?.source !== "bundled"} />
    </div>
  );
}
