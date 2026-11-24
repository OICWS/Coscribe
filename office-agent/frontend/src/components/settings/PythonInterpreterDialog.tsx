import { useEffect, useState } from "react";
import {
  downloadOwnPython,
  getScriptEnvInterpreter,
  retestScriptIsolation,
  setScriptEnvInterpreter,
} from "../../lib/rest";
import type { FoundPython, ScriptEnvInterpreterInfo, ScriptIsolation } from "../../types/settings";
import { filePickerNative } from "../../lib/desktop";
import { CHECK_WORDS } from "./checkWords";
import { SettingsDialog } from "./SettingsDialog";
import { fieldClass, secondaryButtonClass } from "./SettingRow";

type Status = { text: string; error: boolean } | null;

function preparedText(result: ScriptIsolation): Status {
  switch (result.state) {
    case "passed":
      return { text: "Ready. Scripts run isolated with this Python.", error: false };
    case "failed":
      return {
        text: `Ready, but the isolation check failed on this computer (${CHECK_WORDS[result.failed] ?? result.failed}), so scripts are off. A conversation can still allow them under Edit workspace › Scripts.`,
        error: true,
      };
    case "setup_failed":
      return { text: `Couldn't set up scripts with this Python. ${result.detail}`, error: true };
    default:
      return { text: "Saved. Scripts use this Python from their next run.", error: false };
  }
}

const failure = (err: unknown, fallback: string): Status => ({
  text: err instanceof Error ? err.message : fallback,
  error: true,
});

// Choosing a Python (or downloading coscribe's own) sets up the scripts' environment and runs the
// isolation check at once, so the person learns here, not at the first script, whether scripts
// work. The download happens only on the person's click (#586).
function usePythonChoice(active: boolean) {
  const [info, setInfo] = useState<ScriptEnvInterpreterInfo | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>(null);
  // Shown checked at once; the save and the setup after it take a while.
  const [picked, setPicked] = useState<string | null | undefined>(undefined);

  const refresh = () => {
    getScriptEnvInterpreter()
      .then(setInfo)
      .catch((err) => setStatus(failure(err, "Could not look for Python.")));
  };

  useEffect(() => {
    if (active) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const apply = async (busyText: string, failText: string, start: () => Promise<{ success: boolean; error: string | null }>) => {
    setBusy(busyText);
    setStatus(null);
    try {
      const result = await start();
      if (!result.success) {
        setStatus({ text: result.error || failText, error: true });
        return;
      }
      refresh();
      setBusy("Setting up scripts with this Python and checking isolation… The first time takes a minute or two.");
      setStatus(preparedText(await retestScriptIsolation()));
    } catch (err) {
      setStatus(failure(err, failText));
    } finally {
      setPicked(undefined);
      setBusy(null);
    }
  };

  const choose = (chosen: string) => {
    setPicked(chosen || null);
    void apply("Checking this Python…", "Could not use that Python.", () => setScriptEnvInterpreter(chosen));
  };
  const download = () =>
    void apply("Downloading Coscribe's Python (about 30 MB)…", "Could not download Python.", downloadOwnPython);

  const configured = picked !== undefined ? picked : (info?.configured ?? null);
  return { info, busy, status, configured, choose, download };
}

interface PythonChoicesProps {
  found: FoundPython[];
  configured: string | null;
  disabled: boolean;
  onChoose: (path: string) => void;
}

function PythonChoices({ found, configured, disabled, onChoose }: PythonChoicesProps) {
  const row = (key: string, checked: boolean, chosen: string, title: string, detail: string, isPath: boolean) => (
    <label key={key} className="flex cursor-pointer items-start gap-3 px-4 py-2.5 text-sm">
      <input
        type="radio"
        name="python-interpreter"
        className="mt-1 h-4 w-4 shrink-0 accent-[var(--accent)]"
        checked={checked}
        disabled={disabled}
        onChange={() => onChoose(chosen)}
      />
      <span className="flex min-w-0 flex-col">
        <span>{title}</span>
        <span className={`truncate text-xs text-[var(--muted)] ${isPath ? "font-mono" : ""}`} title={detail}>
          {detail}
        </span>
      </span>
    </label>
  );
  const other = configured !== null && !found.some((python) => python.path === configured) ? configured : null;
  return (
    <div className="flex flex-col divide-y divide-[var(--border)] overflow-hidden rounded-xl border border-[var(--border)]">
      {row(
        "automatic",
        configured === null,
        "",
        "Automatic",
        found.length > 0 ? "Coscribe picks one that works" : "No Python found on this computer",
        false,
      )}
      {found.map((python) =>
        row(python.path, configured === python.path, python.path, `Python ${python.version}`, python.path, true),
      )}
      {other !== null && row("other", true, other, "Chosen file", other, true)}
    </div>
  );
}

// The download and file buttons stack in one column, so they share a width.
const sideButtonWidth = "w-32 shrink-0";

const PYTHON_FILES = { title: "Choose a Python interpreter", filters: [{ name: "Python", extensions: ["exe"] }, { name: "All files", extensions: ["*"] }] };

/** Another Python by its file: the system's own file picker in the desktop app, a typed path in a
 * browser tab, which has no way to give a page a file's full path. */
function OtherPython({ configured, disabled, onChoose }: { configured: string | null; disabled: boolean; onChoose: (path: string) => void }) {
  const [path, setPath] = useState("");
  const pick = filePickerNative();
  if (pick) {
    const browse = async () => {
      const chosen = await pick(PYTHON_FILES);
      if (chosen && chosen !== configured) onChoose(chosen);
    };
    return (
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px] text-[var(--muted)]">
        <span className="min-w-[12rem] flex-1">Another Python on this computer? Pick its python.exe.</span>
        <button type="button" className={`${secondaryButtonClass} ${sideButtonWidth}`} disabled={disabled} onClick={() => void browse()}>
          Choose file
        </button>
      </div>
    );
  }
  const use = () => {
    const chosen = path.trim();
    if (chosen && chosen !== configured) onChoose(chosen);
  };
  return (
    <div className="flex items-center gap-2">
      <input
        aria-label="Python interpreter path"
        className={`${fieldClass} min-w-0 flex-1 font-mono text-[13px]`}
        placeholder="Or another python.exe path"
        value={path}
        disabled={disabled}
        onChange={(e) => setPath(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && use()}
      />
      <button type="button" className={secondaryButtonClass} disabled={disabled || !path.trim() || path.trim() === configured} onClick={use}>
        Use
      </button>
    </div>
  );
}

/** The interpreter scripts run on, chosen in its own dialog from Settings › Capabilities › Advanced. */
export function PythonInterpreterDialog({ onClose }: { onClose: () => void }) {
  const { info, busy, status, configured, choose, download } = usePythonChoice(true);
  const own = info?.own_python;
  // Looking for every Python on the computer takes a few seconds on Windows.
  const searching = info === null && status === null;

  return (
    <SettingsDialog
      title="Python for scripts"
      description="Which Python runs scripts. Coscribe makes its own environment from it, so nothing you installed is changed."
      onClose={onClose}
    >
      <div className="flex flex-col gap-4">
        {searching && (
          <p role="status" className="flex items-center gap-2 py-2 text-sm text-[var(--muted)]">
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[var(--muted)] border-t-transparent" />
            Searching for Python…
          </p>
        )}

        {info !== null && <PythonChoices found={info.found} configured={configured} disabled={busy !== null} onChoose={choose} />}

        {own?.available && !own.downloaded && (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px] text-[var(--muted)]">
            <span className="min-w-[12rem] flex-1">No suitable Python here? Download Coscribe's own Python {own.version}, about 30 MB.</span>
            <button type="button" className={`${secondaryButtonClass} ${sideButtonWidth}`} disabled={busy !== null} onClick={download}>
              Download
            </button>
          </div>
        )}

        {info !== null && <OtherPython configured={configured} disabled={busy !== null} onChoose={choose} />}

        {busy && <p className="text-[13px] text-[var(--muted)]">{busy}</p>}
        {!busy && status && <p className={`text-[13px] ${status.error ? "text-[var(--danger)]" : "text-[var(--muted)]"}`}>{status.text}</p>}
      </div>
    </SettingsDialog>
  );
}
