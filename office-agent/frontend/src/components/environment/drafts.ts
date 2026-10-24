import { useEffect, useState } from "react";
import { getCapabilities, getScriptIsolation } from "../../lib/rest";
import type { Capabilities, NetworkAccess, ScriptIsolation } from "../../types/settings";

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

/** What this computer allows (Settings › Capabilities) and whether its isolation check passed:
 * an environment can only narrow these. */
export function useMachineLimits() {
  const [isolation, setIsolation] = useState<ScriptIsolation | null>(null);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  useEffect(() => {
    let cancelled = false;
    getScriptIsolation()
      .then((result) => !cancelled && setIsolation(result))
      .catch(() => !cancelled && setIsolation({ state: "failed", failed: "start a script in isolation", detail: "" }));
    getCapabilities()
      .then((result) => !cancelled && setCapabilities(result))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);
  return { isolation, capabilities };
}

export type MachineLimits = ReturnType<typeof useMachineLimits>;

/** How far the environment's conversations may reach the internet; the domains are edited as
 * lines of text. */
export function useNetworkDraft(initial: NetworkAccess) {
  const [mode, setMode] = useState<NetworkAccess["mode"]>(initial.mode);
  const [domains, setDomains] = useState(initial.domains.join("\n"));

  const list = domains
    .split(/[\s,]+/)
    .map((domain) => domain.trim())
    .filter(Boolean);
  // Only limited keeps a list; switching away and back should not lose what was typed.
  const current: NetworkAccess = { mode, domains: mode === "limited" ? list : [] };

  const summary =
    mode === "none"
      ? "None"
      : mode === "full"
        ? "Full"
        : list.includes("*")
          ? "Limited: any site, scripts offline"
          : `Limited: ${list.length} domain${list.length === 1 ? "" : "s"}`;

  return { mode, setMode, domains, setDomains, current, summary };
}

export type NetworkDraft = ReturnType<typeof useNetworkDraft>;

export interface RunSwitches {
  scripts: boolean;
  commands: boolean;
  unisolated: boolean;
}

/** One line for the Scripts and commands row: what this environment's conversations may run. */
export function runSummary(run: RunSwitches, limits: MachineLimits): string {
  const scriptsOn = run.scripts && limits.capabilities?.scripts !== false;
  const commandsOn = run.commands && limits.capabilities?.commands === true;
  const failed = limits.isolation?.state === "failed";
  const scripts = !scriptsOn
    ? "No scripts"
    : failed
      ? run.unisolated
        ? "Scripts without isolation"
        : "No scripts: the isolation check failed"
      : "Scripts";
  return `${scripts}, ${commandsOn ? "commands" : "no commands"}`;
}
