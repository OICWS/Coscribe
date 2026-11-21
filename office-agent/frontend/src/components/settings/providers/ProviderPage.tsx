import { useEffect, useState, type ChangeEvent } from "react";
import { listProviderModels } from "../../../lib/rest";
import type { ProviderCatalogEntry, ProviderInfo } from "../../../types/settings";
import { ArrowLeftIcon, CheckIcon, ExternalLinkIcon } from "../../icons";
import { fieldClass, primaryButtonClass, secondaryButtonClass } from "../SettingRow";
import { ProviderIcon } from "./ProviderIcon";
import { canListModels } from "./catalog";
import { providerKind } from "./kind";

export interface ProviderForm {
  name: string;
  baseUrl: string;
  apiKey: string;
  defaultModel: string;
}

export type ProviderStatus = { text: string; error: boolean } | null;

const labelClass = "flex flex-col gap-1.5";
const labelText = "text-[13px] text-[var(--muted)]";

/** One provider: what it is, where to get a key, and the form that adds it or
 * changes it. With neither `entry` nor `name` it adds a custom provider. */
export function ProviderPage({
  entry,
  name,
  info,
  status,
  onBack,
  onSave,
  onRemove,
}: {
  /** The catalog entry, for a provider Coscribe knows. */
  entry: ProviderCatalogEntry | null;
  /** The configured name, for an added provider the catalog doesn't know. */
  name: string | null;
  info: ProviderInfo | null;
  status: ProviderStatus;
  onBack: () => void;
  onSave: (form: ProviderForm) => Promise<boolean>;
  onRemove: () => void;
}) {
  const isNewCustom = !entry && !name;
  const builtin = entry?.builtin ?? false;
  const title = entry?.title ?? name ?? "Custom provider";
  const [form, setForm] = useState<ProviderForm>({
    name: entry?.name ?? name ?? "",
    baseUrl: info?.base_url ?? entry?.base_url ?? "",
    apiKey: "",
    defaultModel: info?.default_model || entry?.default_model || "",
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      if (await onSave(form)) setForm((f) => ({ ...f, apiKey: "" }));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <button type="button" className="flex w-fit items-center gap-2 text-[15px] text-[var(--fg)] hover:opacity-70" onClick={onBack}>
        <ArrowLeftIcon className="h-4 w-4" /> Providers
      </button>

      <div className="flex items-center gap-5 rounded-xl bg-[var(--card-bg)] px-6 py-6">
        <ProviderIcon name={entry?.name ?? name ?? ""} title={title} size="lg" />
        <div className="min-w-0 flex-1">
          <div className="text-2xl font-semibold">{title}</div>
          <div className="mt-1 text-[15px] text-[var(--muted)]">
            {entry?.description ?? "Any service that speaks the OpenAI chat completions API."}
          </div>
        </div>
        {info && (
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 px-2 text-sm text-[var(--muted)]">
              <CheckIcon className="h-4 w-4" /> Added
            </span>
            <button type="button" className={secondaryButtonClass} onClick={onRemove}>
              Remove
            </button>
          </div>
        )}
      </div>

      {entry?.about && <p className="max-w-[46rem] text-[15px] leading-relaxed">{entry.about}</p>}

      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-[17px] font-medium">{info ? "Settings" : "Add it"}</h3>
          {entry?.key_url && (
            <a
              href={entry.key_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-sm text-[var(--accent)] underline-offset-2 hover:underline"
            >
              {providerKind(entry) === "On this computer" ? `Get ${entry.title}` : "Get an API key"}
              <ExternalLinkIcon className="h-3.5 w-3.5" />
            </a>
          )}
        </div>

        <ProviderFields form={form} onChange={setForm} showName={isNewCustom} builtin={builtin} info={info} />

        <div className="flex items-center justify-end gap-3">
          {status && (
            <span role="status" className={`mr-auto text-sm ${status.error ? "text-[var(--danger)]" : "text-[var(--muted)]"}`}>
              {status.text}
            </span>
          )}
          <button type="button" className={primaryButtonClass} disabled={saving} onClick={() => void save()}>
            {info ? "Save changes" : "Add provider"}
          </button>
        </div>
      </section>
    </div>
  );
}

/** The inputs of the form; a built-in provider has no base URL and a known one no name. */
function ProviderFields({
  form,
  onChange,
  showName,
  builtin,
  info,
}: {
  form: ProviderForm;
  onChange: (form: ProviderForm) => void;
  showName: boolean;
  builtin: boolean;
  info: ProviderInfo | null;
}) {
  const set = (key: keyof ProviderForm) => (e: ChangeEvent<HTMLInputElement>) => onChange({ ...form, [key]: e.target.value });
  const maskedKey = info?.masked_key ?? null;
  return (
    <div className="grid grid-cols-1 gap-x-3 gap-y-3 md:grid-cols-2">
      {showName && (
        <label className={labelClass}>
          <span className={labelText}>Name</span>
          <input className={fieldClass} placeholder="e.g. my-gateway" value={form.name} onChange={set("name")} />
        </label>
      )}
      {!builtin && (
        <label className={labelClass}>
          <span className={labelText}>Base URL</span>
          <input className={fieldClass} placeholder="https://api.example.com/v1" value={form.baseUrl} onChange={set("baseUrl")} />
        </label>
      )}
      <label className={labelClass}>
        <span className={labelText}>API key</span>
        <input
          type="password"
          autoComplete="off"
          className={fieldClass}
          placeholder={maskedKey ? `Saved (ends in ${maskedKey.slice(-4)}). Leave blank to keep it.` : ""}
          value={form.apiKey}
          onChange={set("apiKey")}
        />
      </label>
      <ModelField
        form={form}
        onChange={onChange}
        canList={canListModels(form.name, builtin)}
        listOnOpen={Boolean(info?.masked_key && !info.default_model)}
      />
    </div>
  );
}

type ModelList = { state: "idle" | "loading" } | { state: "listed"; models: string[] } | { state: "failed"; error: string };

/** The default model, typed or picked from what the provider lists at /models. */
function ModelField({
  form,
  onChange,
  canList,
  listOnOpen,
}: {
  form: ProviderForm;
  onChange: (form: ProviderForm) => void;
  /** Whether the provider lists its models at /models (OpenAI-compatible). */
  canList: boolean;
  /** List at once: an added provider without a model can't be picked in the chat. */
  listOnOpen: boolean;
}) {
  const [list, setList] = useState<ModelList>({ state: "idle" });
  const listModels = async () => {
    setList({ state: "loading" });
    try {
      const result = await listProviderModels(form.name.trim(), form.baseUrl.trim(), form.apiKey.trim());
      setList(result.error ? { state: "failed", error: result.error } : { state: "listed", models: result.models });
    } catch (err) {
      setList({ state: "failed", error: err instanceof Error ? err.message : "Couldn't list the models." });
    }
  };
  useEffect(() => {
    if (listOnOpen && canList) void listModels();
    // Only when the page opens: later the person lists on demand.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className={labelClass}>
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor="provider-default-model" className={labelText}>
          Default model
        </label>
        {canList && (
          <button
            type="button"
            className="text-[13px] text-[var(--accent)] underline-offset-2 hover:underline disabled:opacity-50"
            disabled={list.state === "loading"}
            onClick={() => void listModels()}
          >
            {list.state === "loading" ? "Listing models..." : "List the provider's models"}
          </button>
        )}
      </div>
      <input
        id="provider-default-model"
        className={fieldClass}
        placeholder="The model ID the provider lists"
        value={form.defaultModel}
        onChange={(e) => onChange({ ...form, defaultModel: e.target.value })}
      />
      {list.state === "listed" && (
        <select
          aria-label="Models the provider lists"
          className={fieldClass}
          value={list.models.includes(form.defaultModel) ? form.defaultModel : ""}
          onChange={(e) => e.target.value && onChange({ ...form, defaultModel: e.target.value })}
        >
          <option value="">Pick one of {list.models.length} models</option>
          {list.models.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      )}
      {list.state === "failed" && <span className="text-[13px] text-[var(--danger)]">{list.error} Type the model ID instead.</span>}
    </div>
  );
}
