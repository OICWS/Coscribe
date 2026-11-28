import { useRef, useState } from "react";
import { useClickOutside } from "../lib/useClickOutside";
import { CheckIcon } from "./icons";

type Mode = "manual" | "accept-edits" | "plan" | "auto" | "bypass";

// Claude Code's permission modes, in its own order and wording; Bypass only when Settings allows it.
const MODES: { mode: Mode; label: string; description: string }[] = [
  { mode: "manual", label: "Manual", description: "Asks before every change, script or outside action" },
  {
    mode: "accept-edits",
    label: "Accept Edits",
    description: "Edits files in your folders without asking; still asks before running code or outside actions",
  },
  { mode: "plan", label: "Plan", description: "Researches and writes a plan for you to approve before any change" },
  {
    mode: "auto",
    label: "Auto",
    description: "A reviewer model approves routine actions and blocks risky ones instead of asking you",
  },
  {
    mode: "bypass",
    label: "Bypass permissions",
    description: "Runs everything without asking; only hooks, forbidden rules, workspace rules and the sandbox still hold",
  },
];

interface ModePillProps {
  planMode: boolean;
  acceptEdits: boolean;
  autoMode: boolean;
  bypassMode: boolean;
  /** Settings › General's "Allow bypass permissions mode". */
  bypassAllowed: boolean;
  /** Sends a bare user_message with no chat-log bubble -- the backend's
   * "state" reply is the visible confirmation. */
  sendRaw: (text: string) => void;
}

function currentMode({ planMode, acceptEdits, autoMode, bypassMode }: Omit<ModePillProps, "sendRaw" | "bypassAllowed">): Mode {
  if (planMode) return "plan";
  if (acceptEdits) return "accept-edits";
  if (autoMode) return "auto";
  return bypassMode ? "bypass" : "manual";
}

export function ModePill({ planMode, acceptEdits, autoMode, bypassMode, bypassAllowed, sendRaw }: ModePillProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  useClickOutside(rootRef, () => setOpen(false), open);
  const current = currentMode({ planMode, acceptEdits, autoMode, bypassMode });
  const offered = MODES.filter(({ mode }) => mode !== "bypass" || bypassAllowed || current === "bypass");
  // During a reply the server applies a change only when the reply ends.
  const [switchingFrom, setSwitchingFrom] = useState<Mode | null>(null);
  if (switchingFrom !== null && switchingFrom !== current) setSwitchingFrom(null);

  // The server keeps one mode at a time: switching on a mode switches the
  // others off, and switching the current one off returns to Manual.
  const changeMode = (target: Mode) => {
    setOpen(false);
    if (target === current) return;
    setSwitchingFrom(current);
    sendRaw(target === "manual" ? `/${current}` : `/${target}`);
  };

  return (
    <div className="relative min-w-0" ref={rootRef}>
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-8 max-w-full items-center rounded-lg px-2 text-sm text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="truncate">{switchingFrom ? "Switching" : MODES.find((m) => m.mode === current)?.label}</span>
      </button>
      {open && (
        <div
          role="menu"
          className="absolute bottom-full left-0 z-20 mb-1 w-80 whitespace-normal rounded-[10px] border border-[var(--border)] bg-[var(--panel-bg)] p-1 shadow-[var(--shadow)]"
        >
          {offered.map(({ mode, label, description }) => (
            <button
              key={mode}
              type="button"
              role="menuitemradio"
              aria-checked={mode === current}
              className="flex w-full items-start gap-2 rounded-md px-2.5 py-2 text-left hover:bg-[var(--card-bg)]"
              onClick={() => changeMode(mode)}
            >
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="text-sm">{label}</span>
                <span className="text-xs leading-snug text-[var(--muted)]">{description}</span>
              </span>
              {mode === current && <CheckIcon className="mt-0.5 h-4 w-4 shrink-0" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
