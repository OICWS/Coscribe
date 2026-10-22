import { useState } from "react";
import { createDesignSystem, deleteDesignSystem, getDesignSystem, getDesignSystems } from "../../lib/rest";
import { useFetchOnActive } from "../../lib/useFetchOnActive";
import type { DesignSystem, DesignSystemSummary } from "../../types/settings";
import { ConfirmDialog } from "../ConfirmDialog";
import { PlusIcon } from "../icons";
import { DesignSystemEditor } from "./DesignSystemEditor";
import { FetchRetry } from "./FetchRetry";
import { fieldClass, primaryButtonClass, secondaryButtonClass } from "./SettingRow";

const NONE: DesignSystemSummary[] = [];

function shortDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function NewSystemForm({ name, onName, onCreate }: { name: string; onName: (name: string | null) => void; onCreate: () => void }) {
  return (
    <form
      className="flex items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        onCreate();
      }}
    >
      <input
        autoFocus
        aria-label="New design system name"
        className={`${fieldClass} w-72`}
        placeholder="Name, for example your company"
        value={name}
        onChange={(e) => onName(e.target.value)}
      />
      <button type="submit" className={primaryButtonClass} disabled={name.trim() === ""}>
        Create
      </button>
      <button type="button" className={secondaryButtonClass} onClick={() => onName(null)}>
        Cancel
      </button>
    </form>
  );
}

/** Settings > Design systems: the person's library (decision 0020). */
export function DesignSystemsTab({ active }: { active: boolean }) {
  const { data, status, error, retry } = useFetchOnActive(active, getDesignSystems, NONE);
  const [open, setOpen] = useState<DesignSystem | null>(null);
  const [naming, setNaming] = useState<string | null>(null);
  const [removing, setRemoving] = useState<DesignSystemSummary | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const openSystem = async (id: string) => {
    setActionError(null);
    try {
      setOpen(await getDesignSystem(id));
    } catch {
      setActionError("Couldn't open that design system.");
    }
  };

  const create = async () => {
    if (naming === null) return;
    setActionError(null);
    const result = await createDesignSystem(naming);
    if ("error" in result) {
      setActionError(result.error);
      return;
    }
    setNaming(null);
    retry();
    setOpen(result);
  };

  const confirmRemove = async () => {
    if (!removing) return;
    const target = removing;
    setRemoving(null);
    const result = await deleteDesignSystem(target.id);
    if ("error" in result) setActionError(result.error);
    retry();
  };

  if (open) {
    return (
      <DesignSystemEditor
        key={open.id}
        system={open}
        onBack={() => {
          setOpen(null);
          retry();
        }}
        onSaved={() => retry()}
      />
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <h2 className="mr-1 flex-1 text-[22px] font-semibold">Design systems</h2>
        <button type="button" className={`${primaryButtonClass} flex items-center gap-1.5`} disabled={naming !== null} onClick={() => setNaming("")}>
          <PlusIcon className="h-4 w-4" /> New design system
        </button>
      </div>
      <p className="text-sm leading-relaxed text-[var(--muted)]">A design system is your colors, fonts and spacing, kept once. A deck made with one gets a copy, so changing it later does not move a finished deck.</p>
      {actionError && <p role="alert" className="text-sm text-[var(--danger)]">{actionError}</p>}
      {naming !== null && <NewSystemForm name={naming} onName={setNaming} onCreate={() => void create()} />}
      <FetchRetry status={status} error={error} onRetry={retry} />
      {status === "success" && data.length === 0 && naming === null && (
        <p className="py-6 text-center text-sm text-[var(--muted)]">No design systems yet.</p>
      )}
      {data.length > 0 && (
        <ul className="divide-y divide-[var(--border)]">
          {data.map((system) => (
            <li key={system.id} className="flex items-center gap-4 py-3.5">
              <button type="button" className="min-w-0 flex-1 text-left" onClick={() => void openSystem(system.id)}>
                <div className="truncate text-[15px] font-medium">{system.name}</div>
                <div className="mt-0.5 text-xs text-[var(--muted)]">Updated {shortDate(system.updated_at)}</div>
              </button>
              <button type="button" className={secondaryButtonClass} onClick={() => void openSystem(system.id)}>
                Edit
              </button>
              <button type="button" className={secondaryButtonClass} onClick={() => setRemoving(system)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
      {removing && (
        <ConfirmDialog
          title={`Delete ${removing.name}?`}
          description="Decks already made with it keep their own copy. This can't be undone."
          onCancel={() => setRemoving(null)}
          onConfirm={() => void confirmRemove()}
        />
      )}
    </div>
  );
}
