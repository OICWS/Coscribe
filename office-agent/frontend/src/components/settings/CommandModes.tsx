import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { getCommandSandbox, removeCommandSandbox, setUpCommandSandbox } from "../../lib/rest";
import type { CommandSandbox, CommandSandboxMode } from "../../types/settings";
import { ToggleSwitch } from "../ToggleSwitch";
import { secondaryButtonClass } from "./SettingRow";

const POLL_MS = 1000;

/** The command sandbox's state, polled while it is being set up or removed so each step shows. */
export function useCommandSandbox(active: boolean) {
  const [sandbox, setSandbox] = useState<CommandSandbox | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | null>(null);

  const stopPolling = () => {
    if (timer.current !== null) window.clearInterval(timer.current);
    timer.current = null;
  };
  const poll = useCallback(() => {
    stopPolling();
    timer.current = window.setInterval(() => {
      getCommandSandbox().then(
        (next) => {
          setSandbox((prev) => (prev?.state === "working" || next.state === "working" ? next : prev));
          if (next.state !== "working") stopPolling();
        },
        () => undefined,
      );
    }, POLL_MS);
  }, []);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    getCommandSandbox().then(
      (result) => {
        if (cancelled) return;
        setSandbox(result);
        // Set up started before this page opened (or in another window): follow it.
        if (result.state === "working") poll();
      },
      () => undefined,
    );
    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [active, poll]);

  const run = async (action: () => Promise<CommandSandbox | { error: string }>, follow: boolean) => {
    setBusy(true);
    if (follow) poll();
    try {
      const result = await action();
      setSandbox("state" in result ? result : { state: "failed", detail: result.error });
    } catch (err) {
      setSandbox({ state: "failed", detail: err instanceof Error ? err.message : "" });
    } finally {
      stopPolling();
      setBusy(false);
    }
  };

  return {
    sandbox,
    busy: busy || sandbox?.state === "working",
    setUp: (mode: CommandSandboxMode) => void run(() => setUpCommandSandbox(mode), true),
    remove: () => void run(removeCommandSandbox, true),
  };
}

type CommandSandboxControl = ReturnType<typeof useCommandSandbox>;

type Step = { key: string; label: string; elevatedOnly?: boolean };

const SETUP_STEPS: Step[] = [
  { key: "download", label: "Download Codex, which the sandbox is part of" },
  { key: "approve", label: "Wait for an administrator to approve, then create the sandbox's users", elevatedOnly: true },
  { key: "check", label: "Run a test command in it" },
];

const REMOVAL_STEPS: Step[] = [
  { key: "release", label: "Give your private folders their usual permissions back" },
  { key: "uninstall", label: "Wait for an administrator to approve, then remove the sandbox's users", elevatedOnly: true },
];

// The steps that wait on the Windows prompt.
const PROMPTS = new Set(["approve", "uninstall"]);

/** Where set up or removal is: done steps ticked, the current one with its progress or what it
 * waits for. */
function SetupSteps({ sandbox, mode }: { sandbox: CommandSandbox; mode: CommandSandboxMode }) {
  const removing = REMOVAL_STEPS.some((step) => step.key === sandbox.detail);
  const steps = (removing ? REMOVAL_STEPS : SETUP_STEPS).filter((step) => mode === "elevated" || !step.elevatedOnly);
  const current = steps.findIndex((step) => step.key === sandbox.detail);
  return (
    <ol className="mt-2 flex flex-col gap-1 text-[13px]">
      {steps.map((step, index) => {
        const done = index < current;
        const now = index === current;
        let note = "";
        if (now && step.key === "download" && typeof sandbox.progress === "number")
          note = ` ${Math.round(sandbox.progress * 100)}%`;
        return (
          <li key={step.key} className={now ? "text-[var(--fg)]" : "text-[var(--muted)]"}>
            <span aria-hidden className="inline-block w-5">
              {done ? "✓" : now ? "…" : "○"}
            </span>
            {step.label}
            {note}
            {now && PROMPTS.has(step.key) && (
              <span className="mt-0.5 block pl-5 text-[var(--muted)]">
                Look for the Windows prompt, which can open behind other windows; check the taskbar.
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function ModeCard({
  title,
  badge,
  description,
  selected,
  control,
  children,
}: {
  title: string;
  badge?: string;
  description: ReactNode;
  selected: boolean;
  control: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div
      className={`flex flex-col rounded-xl border px-4 py-3 ${
        selected ? "border-[var(--primary)] bg-[var(--card-bg)]" : "border-[var(--border)]"
      }`}
    >
      <div className="flex items-start justify-between gap-6">
        <div className="flex min-w-0 flex-col gap-1">
          <span className="text-[15px] font-medium text-[var(--fg)]">
            {title}
            {badge && (
              <span className="ml-2 rounded-full border border-[var(--border)] px-2 py-0.5 text-[11px] font-normal text-[var(--muted)]">
                {badge}
              </span>
            )}
          </span>
          <span className="text-[13px] leading-snug text-[var(--muted)]">{description}</span>
        </div>
        <div className="shrink-0">{control}</div>
      </div>
      {children}
    </div>
  );
}

function HidePrivateRow({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <div className="mt-3 flex items-center justify-between gap-6 border-t border-[var(--border)] pt-3">
      <div className="flex min-w-0 flex-col gap-1">
        <span className="text-sm text-[var(--fg)]">Hide your private folders from commands</span>
        <span className="text-[13px] leading-snug text-[var(--muted)]">
          {on
            ? "On: a command can't read Documents, Desktop, Downloads, Pictures, Videos, Music, OneDrive or AppData, except the folders of its environment and the programs on your PATH. Other drives and Windows' own folders stay readable."
            : "Off: a command can read most of your files, though it still writes only its environment's folders."}
        </span>
      </div>
      <ToggleSwitch label="Hide your private folders from commands" on={on} onClick={onToggle} />
    </div>
  );
}

/** Set up a sandbox, or remove the one in use; only one is set up at a time. */
function SandboxButton({
  mode,
  inUse,
  busy,
  onSetUp,
  onRemove,
}: {
  mode: CommandSandboxMode;
  inUse: CommandSandboxMode | null;
  busy: boolean;
  onSetUp: (mode: CommandSandboxMode) => void;
  onRemove: () => void;
}) {
  const using = inUse === mode;
  return (
    <button
      type="button"
      className={secondaryButtonClass}
      disabled={busy || (inUse !== null && !using)}
      title={inUse !== null && !using ? "Remove the sandbox in use first." : undefined}
      onClick={() => (using ? onRemove() : onSetUp(mode))}
    >
      {using ? "Remove" : "Set up"}
    </button>
  );
}

interface CommandModesProps {
  control: CommandSandboxControl;
  withoutSandbox: boolean;
  onToggleWithoutSandbox: () => void;
  hidePrivate: boolean;
  onToggleHidePrivate: () => void;
}

/** How a command runs: in the full sandbox, the basic one, or as the person. One is in use at a
 * time; switching between sandboxes means removing the one that is set up. */
export function CommandModes({
  control,
  withoutSandbox,
  onToggleWithoutSandbox,
  hidePrivate,
  onToggleHidePrivate,
}: CommandModesProps) {
  const { sandbox, busy } = control;
  if (sandbox === null) return <p className="py-3 text-sm text-[var(--muted)]">Checking the command sandbox…</p>;
  if (sandbox.state === "unsupported") {
    return (
      <p className="py-3 text-sm text-[var(--muted)]">
        The command sandbox is only available on Windows. Here a command runs as you, and you approve each one.
      </p>
    );
  }
  const ready = sandbox.state === "ready";
  const working = sandbox.state === "working";
  const inUse = ready ? sandbox.mode : null;

  const sandboxControl = (mode: CommandSandboxMode) => (
    <SandboxButton
      mode={mode}
      inUse={inUse ?? null}
      busy={busy}
      onSetUp={control.setUp}
      onRemove={control.remove}
    />
  );
  const failedFor = (mode: CommandSandboxMode) =>
    sandbox.state === "failed" && (sandbox.mode ?? "elevated") === mode ? (
      <p className="mt-2 text-[13px] text-[var(--danger)]">Setting it up didn't work: {sandbox.detail || "no reason given"}</p>
    ) : null;
  const removeFailed = sandbox.error ? (
    <p className="mt-2 text-[13px] text-[var(--danger)]">Removing it didn't work: {sandbox.error}</p>
  ) : null;
  const steps = (mode: CommandSandboxMode) =>
    working && (sandbox.mode ?? "elevated") === mode ? <SetupSteps sandbox={sandbox} mode={mode} /> : null;

  return (
    <div className="flex flex-col gap-3 pt-2">
      <ModeCard
        title="Full sandbox"
        badge={inUse === "elevated" ? "In use" : "Recommended"}
        selected={inUse === "elevated"}
        description="A command runs as a separate Windows user that can write only its environment's folders, can't read your private folders, and is offline unless the environment's network is Full. Setting it up needs an administrator once."
        control={sandboxControl("elevated")}
      >
        {steps("elevated")}
        {failedFor("elevated")}
        {inUse === "elevated" && removeFailed}
        {inUse === "elevated" && <HidePrivateRow on={hidePrivate} onToggle={onToggleHidePrivate} />}
      </ModeCard>
      <ModeCard
        title="Basic sandbox"
        badge={inUse === "unelevated" ? "In use" : "No administrator"}
        selected={inUse === "unelevated"}
        description="A command runs as you with a restricted token: it can still write only its environment's folders, but it can read all your files and is kept offline only by its settings. So you approve each command, in every mode."
        control={sandboxControl("unelevated")}
      >
        {steps("unelevated")}
        {failedFor("unelevated")}
        {inUse === "unelevated" && removeFailed}
      </ModeCard>
      <ModeCard
        title="Without a sandbox"
        selected={inUse === null && withoutSandbox}
        description={
          inUse === null
            ? "A command runs as you and can change or delete any of your files. You approve each one, in every mode, and Auto mode never approves one."
            : "Not used while a sandbox is set up."
        }
        control={
          <ToggleSwitch
            label="Run commands without the sandbox"
            on={inUse === null && withoutSandbox}
            disabled={inUse !== null}
            onClick={onToggleWithoutSandbox}
          />
        }
      />
      <p className="text-[13px] leading-relaxed text-[var(--muted)]">
        Both sandboxes are part of Codex, so setting one up downloads Codex if it isn't there yet. That doesn't turn the
        code module on, which has its own switch below. With no sandbox set up and "Without a sandbox" off, commands are
        refused.
      </p>
    </div>
  );
}
