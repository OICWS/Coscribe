import { useEffect, useState } from "react";
import { getCapabilities, getScriptIsolation } from "../../lib/rest";
import type { Capabilities, NetworkAccess, ScriptIsolation } from "../../types/settings";

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

export type SitesMode = "none" | "listed" | "any";

/** How far the workspace's conversations may reach the internet. "Any site" is kept as limited to
 * every site unless scripts may go online too, which only full allows. */
export function useNetworkDraft(initial: NetworkAccess) {
  const everySite = initial.mode === "full" || initial.domains.includes("*");
  const [mode, setMode] = useState<SitesMode>(initial.mode === "none" ? "none" : everySite ? "any" : "listed");
  const [scriptsOnline, setScriptsOnline] = useState(initial.mode === "full");
  // Kept while another mode is chosen, so switching back does not lose the list.
  const [sites, setSites] = useState(initial.domains.filter((domain) => domain !== "*"));
  const current: NetworkAccess =
    mode === "none"
      ? { mode: "none", domains: [] }
      : mode === "listed"
        ? { mode: "limited", domains: sites }
        : scriptsOnline
          ? { mode: "full", domains: [] }
          : { mode: "limited", domains: ["*"] };
  const add = (site: string) => setSites((list) => (list.includes(site) ? list : [...list, site]));
  const remove = (site: string) => setSites((list) => list.filter((s) => s !== site));
  return { mode, setMode, scriptsOnline, setScriptsOnline, sites, add, remove, current };
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
