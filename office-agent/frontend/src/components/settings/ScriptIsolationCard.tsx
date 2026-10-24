import { useEffect, useState } from "react";
import { getScriptIsolation, retestScriptIsolation } from "../../lib/rest";
import type { ScriptIsolation } from "../../types/settings";
import { CHECK_WORDS } from "../environment/checkWords";
import { secondaryButtonClass } from "./SettingRow";

function headline(status: ScriptIsolation | null, testing: boolean): string {
  if (status === null || testing) return "Checking isolation on this computer…";
  switch (status.state) {
    case "passed":
      return "Scripts run isolated on this computer";
    case "unsupported":
      return "Isolation is only available on Windows";
    case "untested":
      return "Not checked on this computer yet";
    case "setup_failed":
      return "Scripts have no Python to run with yet";
    default:
      return "Isolation doesn't work on this computer, so scripts are off";
  }
}

/** The machine's isolation check: whether a script is held to its folders here, and a way to
 * run the check again. */
export function ScriptIsolationCard({ active }: { active: boolean }) {
  const [status, setStatus] = useState<ScriptIsolation | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    getScriptIsolation()
      .then((result) => !cancelled && setStatus(result))
      .catch(() => !cancelled && setStatus({ state: "failed", failed: "start a script in isolation", detail: "" }));
    return () => {
      cancelled = true;
    };
  }, [active]);

  const retest = async () => {
    setTesting(true);
    try {
      setStatus(await retestScriptIsolation());
    } finally {
      setTesting(false);
    }
  };

  const failed = status?.state === "failed";
  return (
    <div
      className={`flex flex-col gap-2 rounded-xl border px-4 py-3 ${
        failed ? "border-[var(--warning)] bg-[var(--card-bg)]" : "border-[var(--border)]"
      }`}
    >
      <div className="flex items-center gap-3">
        <span className="flex-1 text-[15px] font-medium">{headline(status, testing)}</span>
        {status !== null && status.state !== "unsupported" && (
          <button type="button" className={secondaryButtonClass} disabled={testing} onClick={() => void retest()}>
            {status.state === "untested" ? "Test now" : "Test again"}
          </button>
        )}
      </div>
      {status?.state === "setup_failed" && !testing && (
        <p className="text-[13px] leading-relaxed">
          Choose a Python, or download coscribe's own, below, then test again. {status.detail}
        </p>
      )}
      {failed && !testing && (
        <p className="text-[13px] leading-relaxed">
          {CHECK_WORDS[status.failed] ?? status.failed}. Security software or a company policy can cause this. A
          conversation can still run scripts without isolation from its environment settings.
        </p>
      )}
    </div>
  );
}
