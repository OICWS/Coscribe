import { useCallback, useEffect, useState } from "react";
import { getEnvironments } from "../../lib/rest";
import type { Environment } from "../../types/settings";
import { DEFAULT_ENVIRONMENT, EnvironmentDialog } from "../EnvironmentDialog";
import { PlusIcon } from "../icons";
import { SettingsSection, secondaryButtonClass } from "./SettingRow";

function plural(n: number, noun: string): string {
  return `${n} ${noun}${n === 1 ? "" : "s"}`;
}

/** Where it works and how far it reaches, in a line. */
function accessSummary(environment: Environment): string {
  const folders = environment.folders.length === 0 ? "Default folder" : plural(environment.folders.length, "folder");
  const everySite = environment.network.mode === "full" || environment.network.domains.includes("*");
  const network = environment.network.mode === "none" ? "No internet" : everySite ? "Full internet" : `${plural(environment.network.domains.length, "site")} allowed`;
  const extras = [environment.secrets.length > 0 && plural(environment.secrets.length, "secret"), Object.keys(environment.variables).length > 0 && "Variables"].filter(Boolean);
  return [folders, network, ...extras].join(" · ");
}

function usedBy(environment: Environment): string {
  if (environment.id === DEFAULT_ENVIRONMENT) return "Every conversation that hasn't chosen another";
  const parts = [environment.used_by > 0 && plural(environment.used_by, "conversation"), environment.tasks > 0 && plural(environment.tasks, "scheduled task")].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : "Not used yet";
}

/** Every environment, with Edit on each and New: the same dialog the message box's picker opens. */
export function EnvironmentsSection({ active }: { active: boolean }) {
  const [environments, setEnvironments] = useState<Environment[] | null>(null);
  const [editing, setEditing] = useState<string | null | undefined>(undefined);
  const reload = useCallback(() => {
    getEnvironments()
      .then((result) => setEnvironments(result.environments))
      .catch(() => setEnvironments([]));
  }, []);
  useEffect(() => {
    if (active) reload();
  }, [active, reload]);

  return (
    <SettingsSection
      title="Environments"
      description="An environment is where a conversation works and what it may reach: its folders, the internet, secrets. Choose one for a conversation from the message box."
      action={
        <button type="button" className={`${secondaryButtonClass} flex items-center gap-1.5`} onClick={() => setEditing(null)}>
          <PlusIcon className="h-4 w-4" />
          New
        </button>
      }
    >
      <div className="mt-3 overflow-hidden rounded-xl border border-[var(--border)]">
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_auto] gap-4 border-b border-[var(--border)] px-4 py-2 text-[13px] text-[var(--muted)]">
          <span>Name</span>
          <span>Access</span>
          <span className="w-14" />
        </div>
        {environments === null ? (
          <p className="px-4 py-3 text-sm text-[var(--muted)]">Loading…</p>
        ) : (
          environments.map((environment) => (
            <div key={environment.id} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_auto] items-center gap-4 border-b border-[var(--border)] px-4 py-3 last:border-b-0">
              <div className="flex min-w-0 flex-col">
                <span className="truncate text-[15px] text-[var(--fg)]">{environment.name}</span>
                <span className="truncate text-[13px] text-[var(--muted)]">{usedBy(environment)}</span>
              </div>
              <span className="truncate text-sm text-[var(--muted)]">{accessSummary(environment)}</span>
              <button type="button" aria-label={`Edit ${environment.name}`} className={`${secondaryButtonClass} w-14 !px-0`} onClick={() => setEditing(environment.id)}>
                Edit
              </button>
            </div>
          ))
        )}
      </div>
      {editing !== undefined && <EnvironmentDialog environmentId={editing} onSaved={reload} onDeleted={reload} onClose={() => setEditing(undefined)} />}
    </SettingsSection>
  );
}
