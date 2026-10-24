import { useEffect, useState } from "react";
import {
  downloadOwnPython,
  getScriptEnvInterpreter,
  retestScriptIsolation,
  setScriptEnvInterpreter,
} from "../../lib/rest";
import type { FoundPython, ScriptEnvInterpreterInfo, ScriptIsolation } from "../../types/settings";
import { CHECK_WORDS } from "../environment/checkWords";
import { fieldClass, secondaryButtonClass } from "./SettingRow";

interface PythonInterpreterSectionProps {
  active: boolean;
}

type Status = { text: string; error: boolean } | null;

function preparedText(result: ScriptIsolation): Status {
  switch (result.state) {
    case "passed":
      return { text: "Ready. Scripts run isolated with this Python.", error: false };
    case "failed":
      return {
        text: `Ready, but the isolation check failed on this computer (${CHECK_WORDS[result.failed] ?? result.failed}), so scripts are off. A conversation can still allow them under Edit environment › Scripts.`,
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
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>(null);
  // Shown checked at once; the save and the setup after it take a while.
  const [picked, setPicked] = useState<string | null | undefined>(undefined);

  const refresh = () => {
    getScriptEnvInterpreter()
      .then((loaded) => {
        setInfo(loaded);
        setPath(loaded.configured && !loaded.found.some((f) => f.path === loaded.configured) ? loaded.configured : "");
      })
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
    void apply("Downloading coscribe's Python (about 30 MB)…", "Could not download Python.", downloadOwnPython);

  const configured = picked !== undefined ? picked : (info?.configured ?? null);
  return { info, path, setPath, busy, status, configured, choose, download };
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
  return (
    <div className="flex flex-col divide-y divide-[var(--border)] overflow-hidden rounded-xl border border-[var(--border)]">
      {row(
        "automatic",
        configured === null,
        "",
        "Automatic",
        found.length > 0 ? "coscribe picks one that works" : "No Python found on this computer",
        false,
      )}
      {found.map((python) =>
        row(python.path, configured === python.path, python.path, `Python ${python.version}`, python.path, true),
      )}
    </div>
  );
}

export function PythonInterpreterSection({ active }: PythonInterpreterSectionProps) {
  const { info, path, setPath, busy, status, configured, choose, download } = usePythonChoice(active);
  const own = info?.own_python;

  return (
    <div className="flex flex-col gap-3 pt-4">
      <div>
        <div className="text-[15px]">Interpreter</div>
        <p className="mt-1 text-[13px] leading-snug text-[var(--muted)]">
          Which Python runs scripts. coscribe makes its own environment from it, so nothing you installed is changed.
        </p>
      </div>

      {info !== null && (
        <PythonChoices found={info.found} configured={configured} disabled={busy !== null} onChoose={choose} />
      )}

      {own?.available && !own.downloaded && (
        <div className="flex items-center gap-3 text-[13px] text-[var(--muted)]">
          <span className="flex-1">
            No suitable Python here? coscribe can download its own Python {own.version} from GitHub.
          </span>
          <button type="button" className={secondaryButtonClass} disabled={busy !== null} onClick={download}>
            Download (about 30 MB)
          </button>
        </div>
      )}

      <div className="flex items-center gap-2">
        <input
          aria-label="Python interpreter path"
          className={`${fieldClass} min-w-0 flex-1 font-mono text-[13px]`}
          placeholder="Or another python.exe path"
          value={path}
          disabled={busy !== null}
          onChange={(e) => setPath(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && path.trim() && choose(path.trim())}
        />
        <button
          type="button"
          className={secondaryButtonClass}
          disabled={busy !== null || !path.trim() || path.trim() === configured}
          onClick={() => choose(path.trim())}
        >
          Use
        </button>
      </div>

      {busy && <p className="text-[13px] text-[var(--muted)]">{busy}</p>}
      {!busy && status && (
        <p className={`text-[13px] ${status.error ? "text-red-500" : "text-[var(--muted)]"}`}>{status.text}</p>
      )}
    </div>
  );
}
