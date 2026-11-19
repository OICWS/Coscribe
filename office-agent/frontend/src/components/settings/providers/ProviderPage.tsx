import { useState, type ChangeEvent } from "react";
import type { ProviderCatalogEntry, ProviderInfo } from "../../../types/settings";
import { ArrowLeftIcon, CheckIcon, ExternalLinkIcon } from "../../icons";
import { fieldClass, primaryButtonClass, secondaryButtonClass } from "../SettingRow";
import { ProviderIcon } from "./ProviderIcon";
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

        <ProviderFields form={form} onChange={setForm} showName={isNewCustom} showBaseUrl={!builtin} maskedKey={info?.masked_key ?? null} />

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
  showBaseUrl,
  maskedKey,
}: {
  form: ProviderForm;
  onChange: (form: ProviderForm) => void;
  showName: boolean;
  showBaseUrl: boolean;
  maskedKey: string | null;
}) {
  const set = (key: keyof ProviderForm) => (e: ChangeEvent<HTMLInputElement>) => onChange({ ...form, [key]: e.target.value });
  return (
    <div className="grid grid-cols-1 gap-x-3 gap-y-3 md:grid-cols-2">
      {showName && (
        <label className={labelClass}>
          <span className={labelText}>Name</span>
          <input className={fieldClass} placeholder="e.g. my-gateway" value={form.name} onChange={set("name")} />
        </label>
      )}
      {showBaseUrl && (
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
      <label className={labelClass}>
        <span className={labelText}>Default model (optional)</span>
        <input className={fieldClass} placeholder="The model ID the provider lists" value={form.defaultModel} onChange={set("defaultModel")} />
      </label>
    </div>
  );
}
