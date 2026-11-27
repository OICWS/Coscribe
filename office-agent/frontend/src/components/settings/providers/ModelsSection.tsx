import { useEffect, useState, type MouseEvent } from "react";
import { typedModelRow } from "../../../lib/modelMarks";
import { listProviderModels } from "../../../lib/rest";
import type { ModelRow } from "../../../types/settings";
import { InfoIcon } from "../../modelIcons";
import { ModelTip, type ModelTipAnchor } from "../../ModelTip";
import { ToggleSwitch } from "../../ToggleSwitch";
import { fieldClass, secondaryButtonClass } from "../SettingRow";
import type { ProviderForm } from "./ProviderPage";
import { providerConnection } from "./catalog";

type Listing = { state: "idle" | "loading" } | { state: "listed"; rows: ModelRow[] } | { state: "failed"; error: string };

// Past this many rows a filter is quicker than scrolling.
const FILTER_FROM = 12;

/** Every chat model to show, once each: the saved ones first, so turning one on or off doesn't
 * move it, then what the provider lists for this key. */
function mergeRows(saved: ModelRow[], listed: ModelRow[], turnedOn: string[]): ModelRow[] {
  const byId = new Map<string, ModelRow>();
  for (const row of [...saved, ...listed]) if (row.kind === "chat" && !byId.has(row.id)) byId.set(row.id, row);
  for (const id of turnedOn) if (!byId.has(id)) byId.set(id, typedModelRow(id));
  return [...byId.values()];
}

/** The models this provider's key can use: switch on the ones the model picker should offer. */
export function ModelsSection({
  form,
  providerTitle,
  saved,
  listOnOpen,
  onChange,
}: {
  form: ProviderForm;
  providerTitle: string;
  /** The rows the server has for this provider's turned-on models. */
  saved: ModelRow[];
  listOnOpen: boolean;
  onChange: (form: ProviderForm) => void;
}) {
  const [listing, setListing] = useState<Listing>({ state: "idle" });
  const [filter, setFilter] = useState("");
  const [tip, setTip] = useState<ModelTipAnchor | null>(null);

  const azure = form.apiFormat === "azure";
  const list = async () => {
    setListing({ state: "loading" });
    try {
      const result = await listProviderModels(providerConnection(form));
      setListing(result.error ? { state: "failed", error: result.error } : { state: "listed", rows: result.models });
    } catch (err) {
      setListing({ state: "failed", error: err instanceof Error ? err.message : "Couldn't list the models." });
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

  const rows = mergeRows(saved, !azure && listing.state === "listed" ? listing.rows : [], form.models);
  const q = filter.trim().toLowerCase();
  const shown = rows.filter((r) => !q || `${r.id} ${r.name}`.toLowerCase().includes(q));

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-[17px] font-medium">Models</h3>
        {!azure && <button
          type="button"
          className="text-[13px] text-[var(--accent)] underline-offset-2 hover:underline disabled:opacity-50"
          disabled={listing.state === "loading"}
          onClick={() => void list()}
        >
          {listing.state === "loading" ? "Listing..." : listing.state === "listed" ? "Refresh" : "List models"}
        </button>}
      </div>
      <p className="text-[13px] text-[var(--muted)]">
        {azure ? "Add the Azure deployment name for each model you want to use." : rows.length > 0
          ? "Switch on the models you want in the model picker. Hover one to see what it can do."
          : "List the available models or enter a model ID."}
      </p>

      {rows.length > FILTER_FROM && (
        <input aria-label="Filter models" className={fieldClass} placeholder="Filter models" value={filter} onChange={(e) => setFilter(e.target.value)} />
      )}
      {shown.length > 0 && (
        <ul className="flex max-h-96 flex-col overflow-y-auto rounded-xl border border-[var(--border)]" onScroll={() => setTip(null)}>
          {shown.map((row) => (
            <ModelSwitchRow
              key={row.id}
              row={row}
              on={form.models.includes(row.id)}
              isDefault={row.id === form.defaultModel}
              onToggle={() => toggle(row.id)}
              onMakeDefault={() => onChange({ ...form, defaultModel: row.id })}
              onHover={(anchor) => setTip({ rect: anchor.getBoundingClientRect(), row, provider: providerTitle })}
              onLeave={() => setTip(null)}
            />
          ))}
        </ul>
      )}
      {!azure && listing.state === "failed" && (
        <span role="status" className="text-[13px] text-[var(--muted)]">{listing.error}</span>
      )}
      <ModelIdField azure={azure} onAdd={(id) => !form.models.includes(id) && setModels([...form.models, id])} />
      <ModelTip tip={tip} />
    </section>
  );
}

function ModelSwitchRow({
  row,
  on,
  isDefault,
  onToggle,
  onMakeDefault,
  onHover,
  onLeave,
}: {
  row: ModelRow;
  on: boolean;
  isDefault: boolean;
  onToggle: () => void;
  onMakeDefault: () => void;
  /** With the info icon, which the tip sits beside whichever part of the row is hovered. */
  onHover: (anchor: Element) => void;
  onLeave: () => void;
}) {
  const hover = (e: MouseEvent<HTMLLIElement>) => {
    const icon = e.currentTarget.querySelector("[data-tip-anchor]");
    if (icon) onHover(icon);
  };
  return (
    <li
      className="group flex items-center gap-2 border-b border-[var(--border)] px-4 py-2.5 last:border-b-0 hover:bg-[var(--card-bg)]"
      onMouseEnter={hover}
      onMouseLeave={onLeave}
    >
      <span className="min-w-0 truncate text-sm">{row.name}</span>
      <InfoIcon data-tip-anchor className="h-3.5 w-3.5 shrink-0 text-[var(--muted)]" aria-hidden />
      {isDefault && on && <span className="shrink-0 rounded-md bg-[var(--card-bg)] px-1.5 py-0.5 text-xs text-[var(--muted)]">Default</span>}
      {!isDefault && on && (
        <button
          type="button"
          className="shrink-0 text-xs text-[var(--accent)] opacity-0 hover:underline focus-visible:opacity-100 group-hover:opacity-100"
          onClick={onMakeDefault}
        >
          Make default
        </button>
      )}
      <span className="ml-auto shrink-0">
        <ToggleSwitch on={on} onClick={onToggle} label={`Use ${row.name}`} />
      </span>
    </li>
  );
}

function ModelIdField({ azure, onAdd }: { azure: boolean; onAdd: (id: string) => void }) {
  const [typed, setTyped] = useState("");
  const add = () => {
    if (typed.trim()) onAdd(typed.trim());
    setTyped("");
  };
  return (
    <div className="flex gap-2">
      <input
        aria-label={azure ? "Deployment name" : "Model ID"}
        className={`${fieldClass} min-w-0 flex-1`}
        placeholder={azure ? "Deployment name" : "Model ID"}
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
