import { useEffect, useState } from "react";
import { getSkillPlugins, getSkills, removeSkill, setSkillEnabled } from "../../lib/rest";
import { useFetchOnActive } from "../../lib/useFetchOnActive";
import type { SkillInfo, SkillPlugin } from "../../types/settings";
import { ConfirmDialog } from "../ConfirmDialog";
import { SearchIcon } from "../icons";
import { FetchRetry } from "./FetchRetry";
import { entryMatches, listEntries, matches, type ListEntry } from "./skills/helpers";
import { YoursSections } from "./skills/YoursSections";
import { AddMenu } from "./skills/AddMenu";
import { InstalledPluginView } from "./skills/InstalledPluginView";
import { SkillDetailView } from "./skills/SkillDetailView";
import { PluginCard } from "./skills/PluginCard";
import { PluginDetailView } from "./skills/PluginDetailView";
import { UploadSkillView } from "./skills/UploadSkillView";
import type { View, Tab } from "./skills/types";

interface SkillsTabProps {
  active: boolean;
  /** "Create a skill" in the Add menu -- closes Settings and prefills the
   * composer with "/skill-creator". */
  onCreateSkill: () => void;
}

type PluginEntry = Extract<ListEntry, { kind: "plugin" }>;

/** Settings > Plugins: your plugins and skills and the ones built in (Yours), and Anthropic's
 * open plugins to add (Discover). A skill is a folder with a SKILL.md, a plugin a folder of
 * skills (decision 0058); switching one off stops it being offered in any conversation. */
export function SkillsTab({ active, onCreateSkill }: SkillsTabProps) {
  const { data: skills, status, error, retry } = useFetchOnActive(active, getSkills, []);
  const [view, setView] = useState<View>({ kind: "list" });
  const [tab, setTab] = useState<Tab>("yours");
  const [search, setSearch] = useState("");
  const [catalog, setCatalog] = useState<SkillPlugin[] | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [removeTarget, setRemoveTarget] = useState<SkillInfo | PluginEntry | null>(null);

  const loadCatalog = () => {
    setCatalogError(null);
    getSkillPlugins()
      .then(setCatalog)
      .catch((err: unknown) => setCatalogError(err instanceof Error ? err.message : "Couldn't load Discover."));
  };

  useEffect(() => {
    if (active && tab === "discover" && catalog === null) loadCatalog();
  }, [active, tab, catalog]);

  const toggle = async (target: SkillInfo | PluginEntry) => {
    setActionError(null);
    // A plugin switches as one: every skill of it on, or every one off.
    const names = "info" in target ? target.skills.map((s) => s.name) : [target.name];
    for (const name of names) {
      const result = await setSkillEnabled(name, !target.enabled);
      if ("error" in result) setActionError(result.error);
    }
    retry();
  };

  const confirmRemove = async () => {
    if (!removeTarget) return;
    const target = removeTarget;
    setRemoveTarget(null);
    setActionError(null);
    const result = "info" in target ? await removeSkill(target.info.name, true) : await removeSkill(target.name);
    if ("error" in result) setActionError(result.error);
    setView({ kind: "list" });
    setCatalog(null);
    retry();
  };

  const removeDialog = removeTarget && (
    <ConfirmDialog
      title={"info" in removeTarget ? `Remove the plugin ${removeTarget.info.name}?` : `Remove ${removeTarget.name}?`}
      description={removeDescription(removeTarget)}
      confirmLabel="Remove"
      onCancel={() => setRemoveTarget(null)}
      onConfirm={confirmRemove}
    />
  );

  if (view.kind === "upload") {
    return (
      <UploadSkillView
        onBack={() => setView({ kind: "list" })}
        onUploaded={() => {
          setView({ kind: "list" });
          setTab("yours");
          retry();
        }}
      />
    );
  }

  if (view.kind === "plugin") {
    return (
      <PluginDetailView
        id={view.id}
        onBack={() => setView({ kind: "list" })}
        onAdded={() => {
          setCatalog(null);
          retry();
        }}
      />
    );
  }

  const entries = listEntries(skills);
  const pluginEntry = (name: string) => entries.find((e): e is PluginEntry => e.kind === "plugin" && e.info.name === name);
  const installed = view.kind === "installed" ? pluginEntry(view.name) : undefined;
  if (installed) {
    return (
      <>
        <InstalledPluginView
          entry={installed}
          onBack={() => setView({ kind: "list" })}
          onOpenSkill={(name) => setView({ kind: "detail", name })}
          onToggle={() => toggle(installed)}
          onRemove={() => setRemoveTarget(installed)}
        />
        {removeDialog}
      </>
    );
  }

  const detailSkill = view.kind === "detail" ? skills.find((s) => s.name === view.name) : undefined;
  if (detailSkill) {
    const plugin = detailSkill.plugin;
    return (
      <>
        <SkillDetailView
          skill={detailSkill}
          backLabel={plugin ?? "Your plugins"}
          onBack={() => setView(plugin ? { kind: "installed", name: plugin } : { kind: "list" })}
          onToggle={() => toggle(detailSkill)}
          onRemove={() => setRemoveTarget(detailSkill)}
        />
        {removeDialog}
      </>
    );
  }

  const segment = (active: boolean) =>
    `rounded-md px-3.5 py-1 text-[15px] ${
      active ? "bg-[var(--bg)] text-[var(--fg)] shadow-sm ring-1 ring-[var(--border)]" : "text-[var(--muted)] hover:text-[var(--fg)]"
    }`;
  const visible = entries.filter((e) => entryMatches(search, e));
  const discover = (catalog ?? []).filter((e) => matches(search, e.title, e.description, ...e.skills));

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="mr-1 text-[22px] font-semibold">Plugins</h2>
        <div className="flex rounded-lg bg-[var(--card-bg)] p-0.5">
          <button type="button" aria-pressed={tab === "yours"} className={segment(tab === "yours")} onClick={() => setTab("yours")}>
            Yours
          </button>
          <button type="button" aria-pressed={tab === "discover"} className={segment(tab === "discover")} onClick={() => setTab("discover")}>
            Discover
          </button>
        </div>
        <div className="flex-1" />
        <div className="flex h-9 w-60 items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-3 focus-within:border-[var(--focus)] focus-within:ring-2 focus-within:ring-[var(--focus)]/15">
          <SearchIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
          <input
            aria-label="Search plugins and skills"
            className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--muted)]"
            placeholder="Search plugins and skills"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <AddMenu onUpload={() => setView({ kind: "upload" })} onCreate={onCreateSkill} />
      </div>

      {actionError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {actionError}
        </p>
      )}

      {tab === "yours" ? (
        <>
          <FetchRetry status={status} error={error} onRetry={retry} />
          {status === "success" && (
            <YoursSections
              entries={visible}
              onOpen={(entry) =>
                setView(entry.kind === "plugin" ? { kind: "installed", name: entry.info.name } : { kind: "detail", name: entry.skill.name })
              }
              onToggle={(entry) => toggle(entry.kind === "plugin" ? entry : entry.skill)}
              onRemove={(entry) => setRemoveTarget(entry.kind === "plugin" ? entry : entry.skill)}
            />
          )}
          {status === "success" && visible.length === 0 && (
            <p className="py-6 text-center text-sm text-[var(--muted)]">
              {skills.length === 0 ? "No plugins or skills yet." : `Nothing matches "${search.trim()}".`}
            </p>
          )}
        </>
      ) : (
        <div>
          {catalogError && (
            <p className="text-sm text-[var(--danger)]">
              Couldn't load Discover: {catalogError} --{" "}
              <button type="button" className="underline" onClick={loadCatalog}>
                Retry
              </button>
            </p>
          )}
          {catalog === null && !catalogError && <p className="text-sm text-[var(--muted)]">Loading...</p>}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {discover.map((plugin) => (
              <PluginCard key={plugin.id} plugin={plugin} onOpen={() => setView({ kind: "plugin", id: plugin.id })} />
            ))}
          </div>
          {catalog !== null && discover.length === 0 && (
            <p className="py-6 text-center text-sm text-[var(--muted)]">No plugins match "{search.trim()}".</p>
          )}
          {catalog !== null && (
            <p className="mt-4 text-xs text-[var(--muted)]">
              Open-source skills from github.com/anthropics/skills and github.com/anthropics/knowledge-work-plugins (Apache License 2.0). A plugin is a bundle of skills; Add downloads all of them.
            </p>
          )}
        </div>
      )}
      {removeDialog}
    </div>
  );
}

function removeDescription(target: SkillInfo | PluginEntry): string {
  if ("info" in target) return `Its folder is deleted with its ${target.skills.length} skills. This can't be undone.`;
  const skill = target;
  if (skill.source === "anthropic") return "Its folder is deleted. You can add it again from Discover.";
  return "Its folder is deleted from your skills directory. This can't be undone.";
}
