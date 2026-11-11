import { useEffect, useState } from "react";
import { getProxySettings, saveProxySettings, testProxySettings } from "../../lib/rest";
import type { ProxyMode, ProxySettings, ProxyUpdate } from "../../types/proxy";
import { SegmentedControl } from "./SegmentedControl";
import { fieldClass, secondaryButtonClass, SettingRow, SettingRows, SettingsSection } from "./SettingRow";

const MODES = [
  { value: "system", label: "System", title: "System proxy" },
  { value: "manual", label: "Manual", title: "Manual proxy" },
  { value: "none", label: "No proxy", title: "No proxy" },
] as const;

interface Draft {
  mode: ProxyMode;
  address: string;
  bypass: string;
  username: string;
  /** What was typed; blank keeps the saved password. */
  password: string;
  clearPassword: boolean;
}

function draftOf(saved: ProxySettings): Draft {
  return { mode: saved.mode, address: saved.address, bypass: saved.bypass, username: saved.username, password: "", clearPassword: false };
}

function updateOf(draft: Draft): ProxyUpdate {
  return {
    mode: draft.mode,
    address: draft.address,
    bypass: draft.bypass,
    username: draft.username,
    password: draft.clearPassword ? "" : draft.password || null,
  };
}

function modeDescription(saved: ProxySettings, mode: ProxyMode): string {
  if (mode === "manual") return "One proxy for every connection Coscribe makes.";
  if (mode === "none") return "Connect directly, even if Windows has a proxy set.";
  const now = saved.mode === "system" && saved.active ? ` Now: ${saved.active}.` : "";
  return `The proxy Windows is set to, or one written in .env. A setup script (PAC) is not read.${now}`;
}

function Field({
  label,
  value,
  placeholder,
  type = "text",
  onChange,
}: {
  label: string;
  value: string;
  placeholder?: string;
  type?: "text" | "password";
  onChange: (value: string) => void;
}) {
  return (
    <input aria-label={label} type={type} autoComplete="off" className={`${fieldClass} w-64`} value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
  );
}

function ManualFields({ saved, draft, change }: { saved: ProxySettings; draft: Draft; change: (fields: Partial<Draft>) => void }) {
  // The server keeps a saved password only for the address and user name it was saved with.
  const keepsSaved = saved.password_set && draft.address.trim() === saved.address && draft.username.trim() === saved.username;
  const passwordPlaceholder = draft.clearPassword ? "Will be removed" : keepsSaved ? "Saved" : saved.password_set ? "Enter it again for this proxy" : "Optional";
  return (
    <>
      <SettingRow
        label="Address"
        description="The proxy's host and port."
        control={<Field label="Proxy address" value={draft.address} placeholder="http://proxy.example.com:8080" onChange={(address) => change({ address })} />}
      />
      <SettingRow
        label="Do not use for"
        description="Hosts reached directly, separated by commas. A leading dot covers a whole domain. This computer itself always is."
        control={<Field label="Do not use the proxy for" value={draft.bypass} placeholder="localhost, 127.0.0.1" onChange={(bypass) => change({ bypass })} />}
      />
      <SettingRow
        label="User name"
        description="Only if the proxy asks for one."
        control={<Field label="Proxy user name" value={draft.username} placeholder="Optional" onChange={(username) => change({ username })} />}
      />
      {draft.username && (
        <SettingRow
          label="Password"
          description={
            saved.keychain
              ? "Kept in Windows Credential Manager, never shown again."
              : "This computer has no keychain, so it is kept in Coscribe's settings file, readable only by you."
          }
          control={
            <div className="flex items-center gap-2">
              <Field
                label="Proxy password"
                type="password"
                value={draft.password}
                placeholder={passwordPlaceholder}
                onChange={(password) => change({ password, clearPassword: false })}
              />
              {keepsSaved && !draft.clearPassword && (
                <button type="button" className={secondaryButtonClass} onClick={() => change({ password: "", clearPassword: true })}>
                  Remove
                </button>
              )}
            </div>
          }
        />
      )}
    </>
  );
}

/** Settings › General › Proxy: System, Manual or No proxy. A choice is saved as it is made, the
 * manual fields when focus leaves them, and Coscribe then tries the connection itself. A change
 * applies after a restart. */
export function ProxySection() {
  const [saved, setSaved] = useState<ProxySettings | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [note, setNote] = useState<{ text: string; error: boolean } | null>(null);

  useEffect(() => {
    getProxySettings()
      .then((settings) => {
        setSaved(settings);
        setDraft(draftOf(settings));
      })
      .catch(() => setNote({ text: "Couldn't read the proxy setting.", error: true }));
  }, []);

  if (!saved || !draft) {
    return <SettingsSection title="Proxy">{note && <span className="text-sm text-[var(--danger)]">{note.text}</span>}</SettingsSection>;
  }

  const apply = async (next: Draft) => {
    if (JSON.stringify(next) === JSON.stringify(draftOf(saved))) return;
    if (next.mode === "manual" && !next.address.trim()) return;
    const update = updateOf(next);
    const result = await saveProxySettings(update);
    if ("error" in result) {
      setNote({ text: result.error, error: true });
      return;
    }
    setSaved(result);
    setDraft(draftOf(result));
    const check = await testProxySettings(update);
    const restart = "Applies the next time Coscribe starts.";
    if ("ok" in check && check.ok) setNote({ text: `Saved. Reached ${check.target} ${check.proxy ? `through ${check.proxy}` : "directly"}. ${restart}`, error: false });
    else setNote({ text: `Saved, but the connection didn't work. ${"ok" in check ? (check.error ?? `${check.target} couldn't be reached`) : check.error}`, error: true });
  };
  const change = (fields: Partial<Draft>) => {
    const next = { ...draft, ...fields };
    setDraft(next);
    setNote(null);
    if (fields.mode) void apply(next);
  };

  return (
    <SettingsSection title="Proxy" description="How Coscribe reaches the internet: the model providers, connectors and web tools.">
      <div onBlur={(event) => !event.currentTarget.contains(event.relatedTarget) && void apply(draft)}>
        <SettingRows>
          <SettingRow
            label="Proxy"
            description={
              <>
                {modeDescription(saved, draft.mode)}
                {note && <span className={`mt-1 block ${note.error ? "text-[var(--danger)]" : ""}`}>{note.text}</span>}
              </>
            }
            control={<SegmentedControl value={draft.mode} options={MODES} onChange={(mode) => change({ mode })} />}
          />
          {draft.mode === "manual" && <ManualFields saved={saved} draft={draft} change={change} />}
        </SettingRows>
      </div>
    </SettingsSection>
  );
}
