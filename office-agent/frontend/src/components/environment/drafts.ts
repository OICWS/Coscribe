import { useEffect, useState } from "react";
import {
  getScriptIsolation,
  getThreadNetwork,
  getThreadScripts,
  saveThreadNetwork,
  saveThreadScripts,
} from "../../lib/rest";
import type { NetworkAccess, ScriptIsolation } from "../../types/settings";

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

/** The machine's isolation result and this conversation's choice to run without it, kept until
 * Save changes like the dialog's other pages. */
export function useScriptsDraft(threadId: string) {
  const [status, setStatus] = useState<ScriptIsolation | null>(null);
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
            : status.state === "setup_failed"
              ? "No Python yet"
            : unisolated
              ? "Run without isolation"
              : "Off: the isolation check failed";

  return { status, unisolated, setUnisolated, dirty: unisolated !== loaded, save, summary };
}

export type ScriptsDraft = ReturnType<typeof useScriptsDraft>;

const DEFAULT_NETWORK: NetworkAccess = { mode: "limited", domains: ["*"] };

/** How far this conversation may reach the internet; the domains are edited as lines of text. */
export function useNetworkDraft(threadId: string) {
  const [mode, setMode] = useState<NetworkAccess["mode"]>(DEFAULT_NETWORK.mode);
  const [domains, setDomains] = useState(DEFAULT_NETWORK.domains.join("\n"));
  const [loaded, setLoaded] = useState<NetworkAccess>(DEFAULT_NETWORK);

  useEffect(() => {
    let cancelled = false;
    getThreadNetwork(threadId)
      .then((result) => {
        if (cancelled) return;
        setMode(result.mode);
        setDomains(result.domains.join("\n"));
        setLoaded(result);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [threadId]);

  const list = domains
    .split(/[\s,]+/)
    .map((domain) => domain.trim())
    .filter(Boolean);
  // Only limited keeps a list; switching away and back should not lose what was typed.
  const current: NetworkAccess = { mode, domains: mode === "limited" ? list : [] };
  const dirty = JSON.stringify(current) !== JSON.stringify({ ...loaded, domains: loaded.mode === "limited" ? loaded.domains : [] });

  const save = async (): Promise<string | null> => {
    if (!dirty) return null;
    const result = await saveThreadNetwork(threadId, current);
    return "error" in result ? result.error : null;
  };

  const summary =
    mode === "none"
      ? "None"
      : mode === "full"
        ? "Full"
        : list.includes("*")
          ? "Limited: any site, scripts offline"
          : `Limited: ${list.length} domain${list.length === 1 ? "" : "s"}`;

  return { mode, setMode, domains, setDomains, dirty, save, summary };
}

export type NetworkDraft = ReturnType<typeof useNetworkDraft>;
