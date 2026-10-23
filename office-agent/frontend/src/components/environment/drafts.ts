import { useEffect, useState } from "react";
import { getScriptIsolation, getThreadScripts, retestScriptIsolation, saveThreadScripts } from "../../lib/rest";
import type { ScriptIsolation } from "../../types/settings";

export interface VariableRow {
  key: string;
  value: string;
}

/** The variables to save, or the first name given twice. */
export function toVariables(rows: VariableRow[]): Record<string, string> | string {
  const variables: Record<string, string> = {};
  for (const row of rows) {
    const key = row.key.trim();
    if (!key) continue;
    if (key in variables) return key;
    variables[key] = row.value;
  }
  return variables;
}

/** The machine's isolation check and this conversation's choice to run without it, kept until
 * Save changes like the dialog's other pages. */
export function useScriptsDraft(threadId: string) {
  const [status, setStatus] = useState<ScriptIsolation | null>(null);
  const [testing, setTesting] = useState(false);
  const [unisolated, setUnisolated] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getScriptIsolation()
      .then((result) => !cancelled && setStatus(result))
      .catch(() => !cancelled && setStatus({ state: "failed", failed: "start a script in isolation", detail: "" }));
    getThreadScripts(threadId)
      .then((result) => {
        if (cancelled) return;
        setUnisolated(result.unisolated);
        setLoaded(result.unisolated);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [threadId]);

  const retest = async () => {
    setTesting(true);
    try {
      setStatus(await retestScriptIsolation());
    } finally {
      setTesting(false);
    }
  };

  const save = async (): Promise<string | null> => {
    if (unisolated === loaded) return null;
    const result = await saveThreadScripts(threadId, unisolated);
    return "error" in result ? result.error : null;
  };

  const summary =
    status === null
      ? "Checking…"
      : status.state === "passed"
        ? "Isolated"
        : status.state === "unsupported"
          ? "Isolation needs Windows"
          : status.state === "untested"
            ? "Not checked yet"
            : unisolated
              ? "Run without isolation"
              : "Off: the isolation check failed";

  return { status, testing, retest, unisolated, setUnisolated, dirty: unisolated !== loaded, save, summary };
}

export type ScriptsDraft = ReturnType<typeof useScriptsDraft>;
