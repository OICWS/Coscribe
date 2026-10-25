import { useEffect, useState } from "react";
import { getScriptIsolation } from "../../lib/rest";
import type { ScriptIsolation } from "../../types/settings";

const NOT_ISOLATED: Record<string, string> = {
  failed:
    "Isolation doesn't work on this computer, and this conversation runs scripts without it: the script can read and change any file you can and use the network. Review it before approving.",
  unsupported:
    "Isolation needs Windows: the script can read any file this app can and use the network. It can write only in the workspace and the folders you added, a safeguard against mistakes, not a security boundary. Review it before approving.",
};

/** What holds a script once approved, read from this computer's isolation check (Edit
 * environment > Scripts), so the card never promises a limit the run won't have. */
export function ScriptIsolationNote() {
  const [status, setStatus] = useState<ScriptIsolation | null>(null);
  useEffect(() => {
    let cancelled = false;
    getScriptIsolation()
      .then((result) => !cancelled && setStatus(result))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);
  const warning = status ? NOT_ISOLATED[status.state] : undefined;
  if (warning) {
    return (
      <span className="flex flex-col items-start gap-1">
        <span className="rounded-full border border-[var(--warning)] px-2 py-0.5 font-medium text-[var(--fg)]">
          Not isolated
        </span>
        {warning}
      </span>
    );
  }
  return (
    <>
      {status?.state === "passed"
        ? "Runs isolated: it can use only this conversation's folders, can't delete or rename files there, and reaches the internet only if this conversation's Network setting is Full. Review it before approving."
        : "Coscribe checks isolation on this computer before the script runs, and doesn't run it if the check fails. Review it before approving."}
    </>
  );
}
