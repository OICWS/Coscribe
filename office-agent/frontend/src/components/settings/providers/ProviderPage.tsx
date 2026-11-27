import { useState, type ChangeEvent } from "react";
import type { ProviderCatalogEntry, ProviderFormat, ProviderInfo } from "../../../types/settings";
import { ArrowLeftIcon, CheckIcon, ExternalLinkIcon } from "../../icons";
import { fieldClass, primaryButtonClass, secondaryButtonClass } from "../SettingRow";
import { ProviderIcon } from "./ProviderIcon";
import { providerKind } from "./kind";
import { ModelsSection } from "./ModelsSection";
import { ProviderChecks } from "./ProviderChecks";

export interface ProviderForm {
  name: string;
  baseUrl: string;
  apiKey: string;
  apiFormat?: ProviderFormat;
  apiVersion?: string;
  /** The models turned on, in the order they were turned on. */
  models: string[];
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
  savedForm,
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
  savedForm?: ProviderForm;
  status: ProviderStatus;
  onBack: () => void;
  onSave: (form: ProviderForm) => Promise<boolean>;
  onRemove: () => void;
}) {
  const isNewCustom = !entry && !name;
  const builtin = entry?.builtin ?? false;
  const title = entry?.title ?? name ?? "Custom provider";
  const [form, setForm] = useState<ProviderForm>(savedForm ?? {
    name: entry?.name ?? name ?? "",
    baseUrl: info?.base_url ?? entry?.base_url ?? "",
    apiKey: "",
    apiFormat: info ? info.api_format : "chat_completions",
    apiVersion: info?.api_version ?? "",
    models: info ? info.models.map((m) => m.id) : entry?.default_model ? [entry.default_model] : [],
    defaultModel: info?.default_model || info?.models[0]?.id || entry?.default_model || "",
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

      <ProviderSummary
        name={entry?.name ?? name ?? ""}
        title={title}
        description={entry?.description ?? "Connect your own model service."}
        onRemove={info ? onRemove : undefined}
      />

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
      </section>

      <ModelsSection form={form} providerTitle={title} saved={info?.models ?? []} listOnOpen={(form.apiFormat ?? "chat_completions") === "chat_completions" && Boolean(info?.masked_key)} onChange={setForm} />

      {!builtin && <ProviderChecks form={form} />}

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
    </div>
  );
}

function ProviderSummary({
  name, title, description, onRemove,
}: { name: string; title: string; description: string; onRemove?: () => void }) {
  return (
    <div className="flex items-center gap-5 rounded-xl bg-[var(--card-bg)] px-6 py-6">
      <ProviderIcon name={name} title={title} size="lg" />
      <div className="min-w-0 flex-1">
        <div className="text-2xl font-semibold">{title}</div>
        <div className="mt-1 text-[15px] text-[var(--muted)]">{description}</div>
      </div>
      {onRemove && (
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
  );
}

/** The key inputs of the form; a built-in provider has no base URL and a known one no name. */
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
          <input className={fieldClass} placeholder={form.apiFormat === "azure" ? "https://my-resource.openai.azure.com" : "https://api.example.com/v1"} value={form.baseUrl} onChange={set("baseUrl")} />
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
      {!builtin && (
        <label className={labelClass}>
          <span className={labelText}>API format</span>
          <select className={fieldClass} value={form.apiFormat ?? "chat_completions"} onChange={(e) => onChange({ ...form, apiFormat: e.target.value as ProviderFormat })}>
            <option value="chat_completions">OpenAI compatible (Chat Completions)</option>
            <option value="responses">OpenAI Responses</option>
            <option value="azure">Azure OpenAI (versioned deployments)</option>
          </select>
        </label>
      )}
      {!builtin && form.apiFormat === "azure" && (
        <label className={labelClass}>
          <span className={labelText}>Azure API version</span>
          <input className={fieldClass} placeholder="2024-10-21" value={form.apiVersion ?? ""} onChange={set("apiVersion")} />
          <span className="text-[13px] text-[var(--muted)]">For an endpoint ending in /openai/v1, choose OpenAI compatible instead. It needs no API version.</span>
        </label>
      )}
    </div>
  );
}
