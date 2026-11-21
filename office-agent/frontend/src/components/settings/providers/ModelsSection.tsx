import { useEffect, useState } from "react";
import { listProviderModels } from "../../../lib/rest";
import { typedModelRow } from "../../../lib/modelMarks";
import type { ModelRow } from "../../../types/settings";
import { ModelMarks } from "../../ModelMarks";
import { SelectMenu } from "../../SelectMenu";
import { fieldClass, secondaryButtonClass } from "../SettingRow";
import type { ProviderForm } from "./ProviderPage";

type Listing = { state: "idle" | "loading" } | { state: "listed"; rows: ModelRow[] } | { state: "failed"; error: string };

// Past this many rows a filter is quicker than scrolling.
const FILTER_FROM = 12;

/** Every row to show, once each: the saved ones, then what the provider lists, then IDs typed in. */
function mergeRows(saved: ModelRow[], listed: ModelRow[], turnedOn: string[]): ModelRow[] {
  const byId = new Map<string, ModelRow>();
  for (const row of [...saved, ...listed]) if (!byId.has(row.id)) byId.set(row.id, row);
  for (const id of turnedOn) if (!byId.has(id)) byId.set(id, typedModelRow(id));
  return [...byId.values()];
}

/** The models a provider offers: tick the ones the model picker should show, then the default. */
export function ModelsSection({
  form,
  saved,
  listOnOpen,
  onChange,
}: {
  form: ProviderForm;
  /** The rows the server has for this provider's turned-on models. */
  saved: ModelRow[];
  listOnOpen: boolean;
  onChange: (form: ProviderForm) => void;
}) {
  const [listing, setListing] = useState<Listing>({ state: "idle" });
  const [filter, setFilter] = useState("");

  const list = async () => {
    setListing({ state: "loading" });
    try {
      const result = await listProviderModels(form.name.trim(), form.baseUrl.trim(), form.apiKey.trim());
      setListing(result.error ? { state: "failed", error: result.error } : { state: "listed", rows: result.models });
    } catch (err) {
      setListing({
        state: "failed",
        error: err instanceof Error ? err.message : "Couldn't list the models.",
      });
    }
  };
  useEffect(() => {
    if (listOnOpen) void list();
    // Only when the page opens: later the person lists on demand.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setModels = (models: string[]) => {
    const defaultModel = models.includes(form.defaultModel) ? form.defaultModel : (models[0] ?? "");
    onChange({ ...form, models, defaultModel });
  };
  const toggle = (id: string) => setModels(form.models.includes(id) ? form.models.filter((m) => m !== id) : [...form.models, id]);

  const rows = mergeRows(saved, listing.state === "listed" ? listing.rows : [], form.models);
  const q = filter.trim().toLowerCase();
  const shown = rows.filter((r) => !q || `${r.id} ${r.name}`.toLowerCase().includes(q));
  const chat = shown.filter((r) => r.kind === "chat");
  const other = shown.filter((r) => r.kind !== "chat");

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-[17px] font-medium">Models</h3>
        <button
          type="button"
          className="text-[13px] text-[var(--accent)] underline-offset-2 hover:underline disabled:opacity-50"
          disabled={listing.state === "loading"}
          onClick={() => void list()}
        >
          {listing.state === "loading" ? "Listing models..." : "List the provider's models"}
        </button>
      </div>
      <p className="text-[13px] text-[var(--muted)]">
        The models you turn on are the ones the model picker offers. What each can do comes from a catalog bundled with Coscribe.
      </p>
      {listing.state === "failed" && <span className="text-[13px] text-[var(--danger)]">{listing.error} Add the model ID below instead.</span>}

      {rows.length > FILTER_FROM && (
        <input aria-label="Filter models" className={fieldClass} placeholder="Filter models" value={filter} onChange={(e) => setFilter(e.target.value)} />
      )}
      {chat.length > 0 && (
        <ul className="flex max-h-80 flex-col overflow-y-auto rounded-lg border border-[var(--border)]">
          {chat.map((row) => (
            <ModelCheckRow key={row.id} row={row} on={form.models.includes(row.id)} onToggle={() => toggle(row.id)} />
          ))}
        </ul>
      )}
      <NotForChat rows={other} />
      <TypedModel onAdd={(id) => !form.models.includes(id) && setModels([...form.models, id])} />

      {form.models.length > 0 && (
        <div className="flex items-center justify-between gap-3">
          <span className="text-[13px] text-[var(--muted)]">Default model</span>
          <SelectMenu
            ariaLabel="Default model"
            value={form.defaultModel}
            options={form.models.map((m) => ({ value: m, label: m }))}
            onChange={(v) => onChange({ ...form, defaultModel: v })}
          />
        </div>
      )}
    </section>
  );
}

function ModelCheckRow({ row, on, onToggle }: { row: ModelRow; on: boolean; onToggle: () => void }) {
  return (
    <li className="border-b border-[var(--border)] last:border-b-0">
      <label className="flex cursor-pointer items-start gap-3 px-3 py-2 hover:bg-[var(--card-bg)]">
        <input type="checkbox" className="mt-1" checked={on} onChange={onToggle} />
        <span className="flex min-w-0 flex-col gap-1">
          <span className="truncate text-sm">
            {row.name}
            {row.name !== row.id && <span className="ml-2 text-[12px] text-[var(--muted)]">{row.id}</span>}
          </span>
          <ModelMarks row={row} />
        </span>
      </label>
    </li>
  );
}

/** Embedding, image and other models the provider lists: shown so nothing seems missing, not offered. */
function NotForChat({ rows }: { rows: ModelRow[] }) {
  if (rows.length === 0) return null;
  return (
    <details className="text-sm">
      <summary className="cursor-pointer text-[13px] text-[var(--muted)]">Not for chat ({rows.length})</summary>
      <ul className="mt-2 flex flex-col">
        {rows.map((row) => (
          <li key={row.id} className="px-3 py-1 text-[13px] text-[var(--muted)]">
            {row.id} · {row.kind}
          </li>
        ))}
      </ul>
    </details>
  );
}

/** A model ID typed in, for a provider that doesn't list it. */
function TypedModel({ onAdd }: { onAdd: (id: string) => void }) {
  const [typed, setTyped] = useState("");
  const add = () => {
    if (typed.trim()) onAdd(typed.trim());
    setTyped("");
  };
  return (
    <div className="flex gap-2">
      <input
        aria-label="Model ID"
        className={`${fieldClass} min-w-0 flex-1`}
        placeholder="Add a model ID the provider accepts"
        value={typed}
        onChange={(e) => setTyped(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            add();
          }
        }}
      />
      <button type="button" className={secondaryButtonClass} disabled={!typed.trim()} onClick={add}>
        Add
      </button>
    </div>
  );
}
