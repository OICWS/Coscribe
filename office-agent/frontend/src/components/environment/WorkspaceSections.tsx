import { useState, type ReactNode } from "react";
import { folderName } from "../../lib/folderName";
import type { BrowserLevel, SecretInfo } from "../../types/settings";
import { FolderIcon, PlusIcon } from "../icons";
import { SelectMenu, type SelectOption } from "../SelectMenu";
import { DirBrowserModal } from "../settings";
import { DIR_PERMISSION_OPTIONS, type DirEntry } from "../settings";
import { SegmentedControl } from "../settings";
import { fieldClass, secondaryButtonClass } from "../settings";
import { normalizeSite, patternBase, reachesPattern } from "../../lib/workspaceSites";
import type { NetworkDraft, SitesMode } from "./drafts";

const smallButton = `${secondaryButtonClass} !h-8 !px-2.5 text-[13px]`;
const cell = "border-b border-[var(--border)] py-2 align-middle";

function Section({ title, description, action, children }: { title: string; description: ReactNode; action?: ReactNode; children?: ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <h3 className="text-sm font-medium">{title}</h3>
          <p className="text-[13px] leading-snug text-[var(--muted)]">{description}</p>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

/** The sites the workspace reaches, or null for any. */
function reach(network: NetworkDraft): string[] | null {
  return network.mode === "none" ? [] : network.mode === "any" ? null : network.sites;
}

// Looked up on use, not when the module loads: settings and this feature import each other.
function permissionLabel(permission: string): string {
  return DIR_PERMISSION_OPTIONS.find((option) => option.value === permission)?.label ?? permission;
}

/** A folder Allowed folders doesn't hold yet joins it as read and write when the workspace is saved. */
function accessLabel(permission: string | undefined): string {
  return permission ? permissionLabel(permission) : "Read and write (new)";
}

function PickedFolders({
  more,
  access,
  onRemove,
}: {
  more: string[];
  access: Map<string, DirEntry["permission"]>;
  onRemove: (folder: string) => void;
}) {
  if (more.length === 0) return null;
  return (
    <table className="w-full table-fixed border-collapse text-[13px]">
      <thead>
        <tr className="text-left text-[var(--muted)]">
          <th className={`${cell} w-[34%] py-1.5 font-normal`}>Folder</th>
          <th className={`${cell} py-1.5 font-normal`}>Location</th>
          <th className={`${cell} w-[150px] py-1.5 font-normal`}>Access</th>
          <th className={`${cell} w-[84px] py-1.5`}>
            <span className="sr-only">Remove</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {more.map((folder) => (
          <tr key={folder} className="[&:last-child>td]:border-b-0">
            <td className={`${cell} truncate pr-3`}>{folderName(folder)}</td>
            <td className={`${cell} truncate pr-3 text-[var(--muted)]`} title={folder}>
              {folder}
            </td>
            <td className={`${cell} truncate pr-3 text-[var(--muted)]`}>
              {accessLabel(access.get(folder))}
            </td>
            <td className={`${cell} text-right`}>
              <button type="button" aria-label={`Remove ${folder}`} className={smallButton} onClick={() => onRemove(folder)}>
                Remove
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** The workspace's folder and the Allowed folders it uses (decision 0053): picked from Settings'
 * list, or a new folder, which joins that list as read and write when the workspace is saved. */
export function FoldersSection({
  part,
  folders,
  library,
  onChange,
}: {
  /** The main page shows the workspace's own folder; the Allowed folders page the others. */
  part: "main" | "more";
  folders: string[];
  library: DirEntry[];
  onChange: (folders: string[]) => void;
}) {
  const [browsing, setBrowsing] = useState<"main" | "more" | null>(null);
  const [main, ...more] = folders;
  const access = new Map(library.map((entry) => [entry.path, entry.permission]));
  const unused: SelectOption<string>[] = library
    .filter((entry) => !folders.includes(entry.path))
    .map((entry) => ({ value: entry.path, label: `${folderName(entry.path)} · ${permissionLabel(entry.permission)}` }));
  const pick = (path: string) => {
    if (browsing === "main") onChange([path, ...more.filter((folder) => folder !== path)]);
    else if (!folders.includes(path)) onChange(main === undefined ? [path] : [...folders, path]);
    setBrowsing(null);
  };
  return (
    <>
      {part === "main" && (
        <Section
          title="Folder"
        description="New files, screenshots and artifacts go here."
        action={
          <button type="button" className={`${smallButton} flex items-center gap-1.5`} onClick={() => setBrowsing("main")}>
            <FolderIcon className="h-3.5 w-3.5" />
            {main === undefined ? "Choose" : "Change"}
          </button>
        }
      >
        <span className={`truncate text-[13px] ${main === undefined ? "text-[var(--muted)]" : ""}`} title={main}>
          {main ?? "Coscribe's default workspace folder"}
        </span>
        </Section>
      )}
      {part === "more" && (
        <Section
          title="Allowed folders this workspace uses"
        description="Pick from Allowed folders in Settings, or add a new folder, which joins them as read and write. Other workspaces don't reach these."
        action={
          <div className="flex items-center gap-2">
            {unused.length > 0 && (
              <SelectMenu
                variant="field"
                className="w-[190px]"
                triggerClassName="h-8 text-[13px]"
                ariaLabel="Use an allowed folder"
                placeholder="Use an allowed folder"
                disabled={main === undefined}
                value=""
                options={unused}
                onChange={(path) => onChange([...folders, path])}
              />
            )}
            <button type="button" className={smallButton} disabled={main === undefined} onClick={() => setBrowsing("more")}>
              Add new folder…
            </button>
          </div>
        }
      >
        <PickedFolders more={more} access={access} onRemove={(folder) => onChange(folders.filter((f) => f !== folder))} />
        </Section>
      )}
      {browsing && <DirBrowserModal onClose={() => setBrowsing(null)} onSelect={pick} />}
    </>
  );
}

const SITE_MODES = [
  { value: "none", label: "None" },
  { value: "listed", label: "Listed sites" },
  { value: "any", label: "Any site" },
] as const satisfies readonly { value: SitesMode; label: string }[];

/** A chosen secret none of whose hosts the workspace reaches: it could never be sent. */
function UnreachableSecrets({ network, secrets, chosen }: { network: NetworkDraft; secrets: SecretInfo[]; chosen: Set<string> }) {
  const sites = reach(network);
  if (sites === null) return null;
  const stuck = secrets.filter((secret) => chosen.has(secret.name) && secret.hosts.length > 0 && !secret.hosts.some((host) => reachesPattern(sites, host)));
  return stuck.map((secret) => {
    const host = patternBase(secret.hosts[0]);
    return (
      <div key={secret.name} role="status" className="flex items-center gap-2.5 text-[13px]">
        <span className="h-[7px] w-[7px] shrink-0 rounded-full bg-[var(--warning)]" />
        <span className="min-w-0 flex-1 text-[var(--fg)]">
          {network.mode === "none" ? `${secret.name} can't be sent while this workspace has no internet.` : `${secret.name} is only sent to ${secret.hosts.join(", ")}, which isn't listed.`}
        </span>
        {network.mode === "listed" && (
          <button type="button" className={smallButton} onClick={() => network.add(host)}>
            Add {host}
          </button>
        )}
      </div>
    );
  });
}

const BROWSER_LEVELS = [
  { value: "allow", label: "Use without asking" },
  { value: "ask", label: "Ask each time" },
  { value: "off", label: "Not in the browser" },
] as const satisfies readonly SelectOption<BrowserLevel>[];

const MODE_NOTES: Record<SitesMode, string> = {
  none: "No web search, web pages, downloads or browser steps, and scripts stay offline.",
  listed: "It opens, downloads from and uses in the browser only these sites and their subdomains. Search still works; scripts stay offline.",
  any: "Any site. List one to choose how the browser uses it. Secrets still go only to the hosts set for each one.",
};

/** Where the workspace may go on the internet, and which of its secrets each site gets. */
export function SitesSection({ network, secrets, chosen }: { network: NetworkDraft; secrets: SecretInfo[]; chosen: Set<string> }) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const add = () => {
    const site = normalizeSite(draft);
    if (site === null) {
      setError(`${draft.trim()} isn't a site, such as example.com.`);
      return;
    }
    network.add(site);
    setDraft("");
    setError(null);
  };
  const sentTo = (site: string) =>
    secrets.filter((secret) => chosen.has(secret.name) && secret.hosts.some((host) => reachesPattern([site], host))).map((secret) => secret.name);
  return (
    <Section title="Sites" description={MODE_NOTES[network.mode]} action={<SegmentedControl value={network.mode} options={SITE_MODES} onChange={network.setMode} />}>
      {network.mode !== "none" && (
        <>
          <div className="flex gap-2">
            <input
              aria-label="Add a site"
              className={`${fieldClass} !h-8 min-w-0 flex-1 text-[13px]`}
              placeholder="example.com"
              spellCheck={false}
              value={draft}
              onChange={(e) => {
                setDraft(e.target.value);
                setError(null);
              }}
              onKeyDown={(e) => e.key === "Enter" && draft.trim() && add()}
            />
            <button type="button" aria-label="Add site" disabled={!draft.trim()} className={`${smallButton} !w-8 !px-0 flex items-center justify-center`} onClick={add}>
              <PlusIcon className="h-3.5 w-3.5" />
            </button>
          </div>
          {error && <p className="text-[13px] text-[var(--danger)]">{error}</p>}
          {network.sites.length === 0 ? (
            <p className="text-[13px] text-[var(--muted)]">{network.mode === "listed" ? "No sites yet. Add one, or choose None." : "Add a site to choose how the browser uses it; any other site asks first."}</p>
          ) : (
            <table className="w-full table-fixed border-collapse text-[13px]">
              <thead>
                <tr className="text-left text-[var(--muted)]">
                  <th className={`${cell} py-1.5 font-normal`}>Site</th>
                  <th className={`${cell} w-[196px] py-1.5 font-normal`}>In the browser</th>
                  <th className={`${cell} w-[24%] py-1.5 font-normal`}>Secrets sent</th>
                  <th className={`${cell} w-[84px] py-1.5`}>
                    <span className="sr-only">Remove</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {network.sites.map((site) => {
                  const sent = sentTo(site);
                  return (
                    <tr key={site} className="[&:last-child>td]:border-b-0">
                      <td className={`${cell} truncate pr-3`}>{site}</td>
                      <td className={`${cell} pr-3`}>
                        <SelectMenu
                          variant="field"
                          className="w-[180px]"
                          triggerClassName="h-8 text-[13px]"
                          ariaLabel={`${site} in the browser`}
                          value={network.levelOf(site)}
                          options={BROWSER_LEVELS}
                          onChange={(level) => network.setLevel(site, level)}
                        />
                      </td>
                      <td className={`${cell} truncate pr-3 ${sent.length ? "font-mono text-xs" : "text-[var(--muted)]"}`}>{sent.length ? sent.join(", ") : "None"}</td>
                      <td className={`${cell} text-right`}>
                        <button type="button" aria-label={`Remove ${site}`} className={smallButton} onClick={() => network.remove(site)}>
                          Remove
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </>
      )}
      {network.mode === "any" && (
        <label className="flex items-center gap-2.5 text-[13px]">
          <input type="checkbox" className="h-4 w-4 accent-[var(--primary)]" checked={network.scriptsOnline} onChange={(e) => network.setScriptsOnline(e.target.checked)} />
          Scripts may reach the internet too
        </label>
      )}
      <UnreachableSecrets network={network} secrets={secrets} chosen={chosen} />
    </Section>
  );
}

/** Which secrets the workspace may send; where each may go is the secret's own setting. */
export function SecretsSection({ secrets, chosen, onChange }: { secrets: SecretInfo[]; chosen: Set<string>; onChange: (chosen: Set<string>) => void }) {
  const toggle = (name: string, on: boolean) => {
    const next = new Set(chosen);
    if (on) next.add(name);
    else next.delete(name);
    onChange(next);
  };
  return (
    <Section title="Secrets" description="Which secrets this workspace may send in a web request. The assistant never sees a value. Where each one may go is set in Settings › Secrets.">
      {secrets.length === 0 ? (
        <p className="text-[13px] text-[var(--muted)]">No secrets yet. Add them in Settings › Secrets.</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {secrets.map((secret) => (
            <label key={secret.name} className="flex cursor-pointer items-center gap-2.5 py-0.5 text-[13px]">
              <input type="checkbox" className="h-4 w-4 shrink-0 accent-[var(--primary)]" checked={chosen.has(secret.name)} onChange={(e) => toggle(secret.name, e.target.checked)} />
              <span className="min-w-0 flex-1 truncate font-mono text-xs">{secret.name}</span>
              <span className="min-w-0 truncate text-[var(--muted)]">{secret.hosts.join(", ")}</span>
            </label>
          ))}
        </div>
      )}
    </Section>
  );
}
