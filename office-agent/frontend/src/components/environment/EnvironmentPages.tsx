import { useState } from "react";
import type { SecretInfo } from "../../types/settings";
import { folderName, readRecent } from "../../lib/recentFolders";
import { ChevronRightIcon, PlusIcon } from "../icons";
import { DirBrowserModal } from "../settings/DirBrowserModal";
import { fieldClass } from "../settings/SettingRow";

const emptyClass =
  "rounded-xl border border-dashed border-[var(--border)] px-4 py-4 text-center text-sm text-[var(--muted)]";
const introClass = "text-[13px] leading-relaxed text-[var(--muted)]";

/** One line of the dialog's first page: what a page holds, opened with a click. */
export function EnvironmentRow({ title, value, onOpen }: { title: string; value: string; onOpen: () => void }) {
  return (
    <button
      type="button"
      className="flex w-full items-center gap-3 rounded-xl border border-[var(--border)] px-4 py-3 text-left hover:bg-[var(--card-bg)]"
      onClick={onOpen}
    >
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-[15px] font-medium">{title}</span>
        <span className="truncate text-sm text-[var(--muted)]">{value}</span>
      </span>
      <ChevronRightIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
    </button>
  );
}

const VARIABLES_PLACEHOLDER = `NODE_ENV=production
GIT_AUTHOR_NAME=Your Name

# Multiline values - wrap in quotes
CONFIG="key1=val1
key2=val2"`;

export function VariablesPage({ text, onChange }: { text: string; onChange: (text: string) => void }) {
  return (
    <section className="flex flex-col gap-3">
      <textarea
        aria-label="Environment variables"
        className={`${fieldClass} h-48 resize-y font-mono text-[13px] leading-relaxed`}
        value={text}
        placeholder={VARIABLES_PLACEHOLDER}
        spellCheck={false}
        autoCapitalize="off"
        autoCorrect="off"
        onChange={(e) => onChange(e.target.value)}
      />
      <p className={introClass}>
        One KEY=value per line, in .env format; # starts a comment and a quoted value may span lines. Plain text the
        assistant can read, such as a mode or a project name. For a key, use a secret. Scripts and the code module's
        commands get them as environment variables too, so a name such as PATH, PYTHONPATH, NODE_OPTIONS or a proxy
        variable changes how they run.
      </p>
    </section>
  );
}

export function SecretsPage({
  secrets,
  chosen,
  onChange,
}: {
  secrets: SecretInfo[];
  chosen: Set<string>;
  onChange: (chosen: Set<string>) => void;
}) {
  const toggle = (name: string, on: boolean) => {
    const next = new Set(chosen);
    if (on) next.add(name);
    else next.delete(name);
    onChange(next);
  };
  return (
    <section className="flex flex-col gap-3">
      <p className={introClass}>
        The assistant never sees a secret's value. It can use the ones you tick in a web request, for the hosts shown.
        None by default.
      </p>
      {secrets.length === 0 ? (
        <p className={emptyClass}>No secrets yet. Add them in Settings &gt; Secrets.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {secrets.map((secret) => (
            <li key={secret.name}>
              <label
                className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3.5 py-3 hover:bg-[var(--card-bg)] ${
                  chosen.has(secret.name) ? "border-[var(--accent)]" : "border-[var(--border)]"
                }`}
              >
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--accent)]"
                  checked={chosen.has(secret.name)}
                  onChange={(e) => toggle(secret.name, e.target.checked)}
                />
                <span className="min-w-0">
                  <span className="block font-mono text-sm">{secret.name}</span>
                  <span className="mt-1 flex flex-wrap gap-1">
                    {secret.hosts.map((host) => (
                      <span
                        key={host}
                        className="rounded-md bg-[var(--card-bg)] px-1.5 py-0.5 font-mono text-xs text-[var(--muted)]"
                      >
                        {host}
                      </span>
                    ))}
                  </span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** The environment's folders, the main one first. Which folders exist and how far they may
 * be used is managed in Settings > Workspace; this only picks this environment's. */
export function FoldersPage({ folders, onChange }: { folders: string[]; onChange: (folders: string[]) => void }) {
  const [browsing, setBrowsing] = useState(false);
  // Fixed when the page opens, so a folder unticked here stays listed to tick again.
  const [offered] = useState(() => [...folders, ...readRecent().filter((path) => !folders.includes(path))]);
  const [added, setAdded] = useState<string[]>([]);
  const rows = [...offered, ...added.filter((path) => !offered.includes(path))];
  const toggle = (path: string, on: boolean) =>
    onChange(on ? [...folders, path] : folders.filter((folder) => folder !== path));
  return (
    <section className="flex flex-col gap-3">
      <p className={introClass}>
        The folders this environment's conversations work in. New files go to the main one. With none ticked they use the default
        workspace. Which other folders it may read or change is set in Settings &gt; Workspace.
      </p>
      {rows.length === 0 ? (
        <p className={emptyClass}>The default workspace.</p>
      ) : (
        <ul className="flex flex-col divide-y divide-[var(--border)] overflow-hidden rounded-xl border border-[var(--border)]">
          {rows.map((path) => (
            <li key={path}>
              <label className="flex cursor-pointer items-center gap-3 px-3.5 py-2.5 hover:bg-[var(--card-bg)]" title={path}>
                <input
                  type="checkbox"
                  className="h-4 w-4 shrink-0 accent-[var(--accent)]"
                  checked={folders.includes(path)}
                  onChange={(e) => toggle(path, e.target.checked)}
                />
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate text-sm">{folderName(path)}</span>
                  <span className="truncate text-xs text-[var(--muted)]">{path}</span>
                </span>
                {folders[0] === path && (
                  <span className="shrink-0 rounded-full bg-[var(--card-bg)] px-2 py-0.5 text-xs text-[var(--muted)]">
                    Main
                  </span>
                )}
              </label>
            </li>
          ))}
        </ul>
      )}
      <button
        type="button"
        className="flex w-fit items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--card-bg)]"
        onClick={() => setBrowsing(true)}
      >
        <PlusIcon className="h-4 w-4" /> Add folder…
      </button>
      {browsing && (
        <DirBrowserModal
          onClose={() => setBrowsing(false)}
          onSelect={(path) => {
            setBrowsing(false);
            setAdded((current) => (current.includes(path) ? current : [...current, path]));
            if (!folders.includes(path)) onChange([...folders, path]);
          }}
        />
      )}
    </section>
  );
}
