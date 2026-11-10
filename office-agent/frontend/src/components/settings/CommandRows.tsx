import { useEffect, useRef, useState } from "react";
import type { Capabilities, CommandSandbox } from "../../types/settings";
import { ConfirmDialog } from "../ConfirmDialog";
import { SelectMenu } from "../SelectMenu";
import { ToggleSwitch } from "../ToggleSwitch";
import { secondaryButtonClass, SettingRow, SubRows } from "./SettingRow";
import type { useCommandSandbox } from "./useCommandSandbox";

type SandboxChoice = "none" | "basic" | "full";

const SANDBOX_OPTIONS: { value: SandboxChoice; label: string }[] = [
  { value: "basic", label: "Basic sandbox" },
  { value: "full", label: "Full sandbox" },
  { value: "none", label: "No sandbox" },
];

const SANDBOX_TEXT: Record<SandboxChoice, string> = {
  basic: "A command can write only its environment's folders, but can read your files. No administrator needed.",
  full: "A command runs as a separate Windows user: it can write only its environment's folders and can't read your private folders. Needs an administrator once.",
  none: "A command runs as you and can change any of your files.",
};

function sandboxChoice(sandbox: CommandSandbox | null): SandboxChoice {
  if (sandbox?.state !== "ready") return "none";
  return sandbox.mode === "unelevated" ? "basic" : "full";
}

/** Moves the command sandbox to the one picked: removes the one in use, sets the other up, and
 * goes back to what was there when that fails (the full sandbox needs an administrator). */
function useSandboxChoice(control: ReturnType<typeof useCommandSandbox>) {
  const { sandbox, busy } = control;
  const current = sandboxChoice(sandbox);
  const [wanted, setWanted] = useState<SandboxChoice | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const previous = useRef<SandboxChoice>("none");
  const attempted = useRef<SandboxChoice | null>(null);
  useEffect(() => {
    if (wanted === null || busy || sandbox === null) return;
    if (wanted === current) {
      attempted.current = null;
      setWanted(null);
    } else if (sandbox.state === "ready") {
      control.remove();
    } else if (attempted.current !== wanted) {
      attempted.current = wanted;
      control.setUp(wanted === "full" ? "elevated" : "unelevated");
    } else {
      const back = previous.current === wanted ? "none" : previous.current;
      setNotice(
        `${wanted === "full" ? "Windows didn't give an administrator's approval, so the full sandbox wasn't set up" : "The basic sandbox couldn't be set up"}. Still using: ${SANDBOX_OPTIONS.find((o) => o.value === back)?.label.toLowerCase()}.`,
      );
      attempted.current = null;
      previous.current = back;
      setWanted(back === "none" ? null : back);
    }
  }, [wanted, busy, sandbox, current, control]);
  const pick = (choice: SandboxChoice) => {
    if (choice === current && wanted === null) return;
    setNotice(null);
    previous.current = current;
    attempted.current = null;
    setWanted(choice);
  };
  return { value: wanted ?? current, working: wanted !== null || busy, notice, pick };
}

// Turning commands on, and then letting them run outside the sandbox, are two separate risks,
// each confirmed once (decision 0022).
const CONFIRMATIONS = {
  commands: {
    title: "Turn on commands?",
    description:
      "Coscribe sets up the basic command sandbox, where a command can write only its environment's folders. You approve each command. Turning this on is recorded in the audit log.",
    confirmLabel: "Turn on",
  },
  commands_without_sandbox: {
    title: "Run commands without the sandbox?",
    description:
      "A command would run as you, with nothing to hold it to its folders: one you approve can change or delete any of your files and reach the internet. Coscribe asks before each command, in every mode, and never lets Auto mode approve one.",
    confirmLabel: "Allow",
  },
} as const;

interface CommandRowsProps {
  capabilities: Capabilities;
  set: (name: keyof Capabilities, on: boolean) => void;
  control: ReturnType<typeof useCommandSandbox>;
  onOpenEnvironments: () => void;
}

/** Run commands, and under it the sandbox they run in. Coscribe sets the sandbox up itself; a
 * person only picks which one. */
export function CommandRows({ capabilities, set, control, onOpenEnvironments }: CommandRowsProps) {
  const [confirm, setConfirm] = useState<keyof typeof CONFIRMATIONS | null>(null);
  const sandbox = control.sandbox;
  const choice = useSandboxChoice(control);
  const supported = sandbox !== null && sandbox.state !== "unsupported";
  const pickSandbox = (next: SandboxChoice) => {
    if (next === "none" && !capabilities.commands_without_sandbox) setConfirm("commands_without_sandbox");
    else choice.pick(next);
  };
  const confirmed = (what: keyof typeof CONFIRMATIONS) => {
    setConfirm(null);
    set(what, true);
    if (what === "commands_without_sandbox") choice.pick("none");
    else if (supported && sandbox.state !== "ready") choice.pick("basic");
  };
  return (
    <>
      <SettingRow
        label="Run commands"
        description="Command lines in cmd or PowerShell, for what a script can't do: git, build tools, installers. You approve each one."
        control={<ToggleSwitch label="Run commands" on={capabilities.commands} onClick={() => (capabilities.commands ? set("commands", false) : setConfirm("commands"))} />}
      />
      {capabilities.commands && (
        <SubRows>
          <SettingRow
            label="Command sandbox"
            description={
              sandbox?.state === "unsupported" ? (
                "Only available on Windows. Here a command runs as you, and you approve each one."
              ) : (
                <>
                  {SANDBOX_TEXT[choice.value]}
                  {choice.working && <span className="mt-1 block">Setting it up… If Windows asks for an administrator, check the taskbar.</span>}
                  {choice.notice && <span className="mt-1 block text-[var(--danger)]">{choice.notice}</span>}
                </>
              )
            }
            control={supported ? <SelectMenu ariaLabel="Command sandbox" value={choice.value} options={SANDBOX_OPTIONS} onChange={pickSandbox} /> : null}
          />
          <SettingRow
            label="Private folders"
            description="In the full sandbox a command can't read Documents, Desktop, Downloads, Pictures or OneDrive. To let commands read a folder there, add it to an environment or to Other folders."
            control={
              <button type="button" className={secondaryButtonClass} onClick={onOpenEnvironments}>
                Manage
              </button>
            }
          />
        </SubRows>
      )}
      {confirm && <ConfirmDialog {...CONFIRMATIONS[confirm]} onCancel={() => setConfirm(null)} onConfirm={() => confirmed(confirm)} />}
    </>
  );
}
