import { useCallback, useEffect, useRef, useState } from "react";
import { deleteEnvironment, getEnvironments } from "../../lib/rest";
import type { Environment } from "../../types/settings";
import { ConfirmDialog } from "../ConfirmDialog";
import { DEFAULT_ENVIRONMENT, EnvironmentDialog, whereItsConversationsGo } from "../EnvironmentDialog";
import { MoreIcon, PencilIcon, PlusIcon, TrashIcon } from "../icons";
import { itemClass, menuClass } from "../menuStyle";
import { SettingsSection, secondaryButtonClass } from "./SettingRow";

function plural(n: number, noun: string): string {
  return `${n} ${noun}${n === 1 ? "" : "s"}`;
}

/** How far it reaches beyond its folders, in a line. */
function accessSummary(environment: Environment): string {
  const everySite = environment.network.mode === "full" || environment.network.domains.includes("*");
  const network = environment.network.mode === "none" ? "No internet" : everySite ? "Full internet" : `${plural(environment.network.domains.length, "site")} allowed`;
  const extras = [environment.secrets.length > 0 && plural(environment.secrets.length, "secret"), Object.keys(environment.variables).length > 0 && "Variables"].filter(Boolean);
  return [network, ...extras].join(" · ");
}

function usedBy(environment: Environment): string {
  if (environment.id === DEFAULT_ENVIRONMENT) return "Every conversation that hasn't chosen another";
  const parts = [environment.used_by > 0 && plural(environment.used_by, "conversation"), environment.tasks > 0 && plural(environment.tasks, "scheduled task")].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : "Not used yet";
}

const columns = "grid grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_minmax(0,1fr)_32px] gap-4";

function RowMenu({ environment, onEdit, onDelete }: { environment: Environment; onEdit: () => void; onDelete: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => !ref.current?.contains(event.target as Node) && setOpen(false);
    window.addEventListener("mousedown", onPointer);
    return () => window.removeEventListener("mousedown", onPointer);
  }, [open]);
  const choose = (action: () => void) => () => {
    setOpen(false);
    action();
  };
  return (
    <div
      ref={ref}
      className="relative"
      onKeyDown={(event) => {
        // Taken here so Settings, which closes on Escape, stays open.
        if (open && event.key === "Escape") {
          event.stopPropagation();
          setOpen(false);
        }
      }}
    >
      <button
        type="button"
        aria-label={`${environment.name} actions`}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-8 w-8 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
        onClick={() => setOpen(!open)}
      >
        <MoreIcon className="h-4 w-4 rotate-90" />
      </button>
      {open && (
        <div role="menu" aria-label={`${environment.name} actions`} className={`${menuClass} absolute right-0 top-full mt-1 w-40`}>
          <button type="button" role="menuitem" className={itemClass} onClick={choose(onEdit)}>
            <PencilIcon className="h-3.5 w-3.5" /> Edit
          </button>
          {environment.id !== DEFAULT_ENVIRONMENT && (
            <button type="button" role="menuitem" className={`${itemClass} text-[var(--danger)]`} onClick={choose(onDelete)}>
              <TrashIcon className="h-3.5 w-3.5" /> Delete
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/** Every environment in a table, edited in the same dialog the message box's picker opens. */
export function EnvironmentsSection({ active }: { active: boolean }) {
  const [environments, setEnvironments] = useState<Environment[] | null>(null);
  const [editing, setEditing] = useState<string | null | undefined>(undefined);
  const [deleting, setDeleting] = useState<Environment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reload = useCallback(() => {
    getEnvironments()
      .then((result) => setEnvironments(result.environments))
      .catch(() => setEnvironments([]));
  }, []);
  useEffect(() => {
    if (active) reload();
  }, [active, reload]);

  const remove = async (environment: Environment) => {
    setDeleting(null);
    const result = await deleteEnvironment(environment.id);
    setError("error" in result ? result.error : null);
    reload();
  };

  return (
    <SettingsSection
      title={environments ? `Environments (${environments.length})` : "Environments"}
      description="An environment is a folder you work in. Its conversations and tasks reach that folder, the allowed folders below, and the sites and secrets you give it. Choose one for a conversation under the message box."
      action={
        <button type="button" className={`${secondaryButtonClass} flex items-center gap-1.5`} onClick={() => setEditing(null)}>
          <PlusIcon className="h-4 w-4" />
          New
        </button>
      }
    >
      <div role="table" aria-label="Environments" className="mt-3 rounded-xl border border-[var(--border)] text-[13px]">
        <div role="row" className={`${columns} border-b border-[var(--border)] py-2.5 pl-4 pr-2 text-[var(--muted)]`}>
          <span role="columnheader">Name</span>
          <span role="columnheader">Folder</span>
          <span role="columnheader">Access</span>
          <span role="columnheader" className="sr-only">
            Actions
          </span>
        </div>
        {environments === null ? (
          <p className="px-4 py-3 text-[var(--muted)]">Loading…</p>
        ) : (
          environments.map((environment) => {
            const [main, ...others] = environment.folders;
            return (
              <div key={environment.id} role="row" className={`${columns} items-center border-b border-[var(--border)] py-2 pl-4 pr-2 last:border-b-0`}>
                <div role="cell" className="flex min-w-0 flex-col">
                  <span className="truncate text-sm text-[var(--fg)]">{environment.name}</span>
                  <span className="truncate text-[var(--muted)]">{usedBy(environment)}</span>
                </div>
                <span role="cell" className="truncate text-[var(--muted)]" title={environment.folders.join("\n") || undefined}>
                  {main ?? "Default workspace folder"}
                  {others.length > 0 && ` +${others.length}`}
                </span>
                <span role="cell" className="truncate text-[var(--muted)]">
                  {accessSummary(environment)}
                </span>
                <div role="cell">
                  <RowMenu environment={environment} onEdit={() => setEditing(environment.id)} onDelete={() => setDeleting(environment)} />
                </div>
              </div>
            );
          })
        )}
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm text-[var(--danger)]">
          {error}
        </p>
      )}
      {editing !== undefined && <EnvironmentDialog environmentId={editing} onSaved={reload} onDeleted={reload} onClose={() => setEditing(undefined)} />}
      {deleting && (
        <ConfirmDialog
          title={`Delete ${deleting.name}?`}
          description={whereItsConversationsGo(deleting)}
          onCancel={() => setDeleting(null)}
          onConfirm={() => void remove(deleting)}
        />
      )}
    </SettingsSection>
  );
}
