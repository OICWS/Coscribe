import { ToggleSwitch } from "../ToggleSwitch";
import type { MachineLimits, RunSwitches } from "./drafts";

function SwitchRow({
  label,
  detail,
  on,
  disabled,
  onClick,
}: {
  label: string;
  detail: string;
  on: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-[var(--border)] px-4 py-3">
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="text-[15px] font-medium">{label}</span>
        <span className="text-[13px] leading-relaxed text-[var(--muted)]">{detail}</span>
      </span>
      <ToggleSwitch label={label} on={on} disabled={disabled} onClick={onClick} />
    </div>
  );
}

/** What the environment's conversations may run, within what Settings › Capabilities allows. */
export function ScriptsPage({
  run,
  limits,
  onChange,
}: {
  run: RunSwitches;
  limits: MachineLimits;
  onChange: (run: RunSwitches) => void;
}) {
  const scriptsOff = limits.capabilities?.scripts === false;
  const commandsOff = limits.capabilities?.commands !== true;
  const failed = limits.isolation?.state === "failed";
  return (
    <section className="flex flex-col gap-3">
      <p className="text-[13px] leading-relaxed text-[var(--muted)]">
        Settings › Capabilities decides what may run on this computer; here you can turn it off for this environment.
      </p>
      <SwitchRow
        label="Scripts"
        detail={
          scriptsOff
            ? "Off in Settings › Capabilities."
            : "Python and Node.js scripts, isolated to this environment's folders."
        }
        on={run.scripts && !scriptsOff}
        disabled={scriptsOff}
        onClick={() => onChange({ ...run, scripts: !run.scripts })}
      />
      <SwitchRow
        label="Commands"
        detail={
          commandsOff
            ? "Off in Settings › Capabilities."
            : "cmd and PowerShell. A command runs as you; you approve each one."
        }
        on={run.commands && !commandsOff}
        disabled={commandsOff}
        onClick={() => onChange({ ...run, commands: !run.commands })}
      />
      {failed && !scriptsOff && (
        <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-[var(--border)] px-4 py-3">
          <input
            type="checkbox"
            role="switch"
            className="mt-1 h-4 w-4 shrink-0 accent-[var(--accent)]"
            checked={run.unisolated}
            onChange={(e) => onChange({ ...run, unisolated: e.target.checked })}
          />
          <span className="flex flex-col gap-1">
            <span className="text-[15px] font-medium">Run scripts without isolation</span>
            <span className="text-[13px] leading-relaxed text-[var(--muted)]">
              The isolation check failed on this computer, so scripts are off. This turns them on in this environment
              only: a script then runs as you and can reach anything you can. You still approve each one, and turning
              this on is recorded in the audit log.
            </span>
          </span>
        </label>
      )}
    </section>
  );
}
