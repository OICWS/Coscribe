import { useEffect, useRef, useState } from "react";
import { getSkillPlugins, getSkills, removeSkill, setSkillEnabled } from "../../lib/rest";
import { useClickOutside } from "../../lib/useClickOutside";
import { useFetchOnActive } from "../../lib/useFetchOnActive";
import type { SkillInfo, SkillPlugin } from "../../types/settings";
import { ConfirmDialog } from "../ConfirmDialog";
import { ChevronDownIcon, PencilIcon, PlusIcon, SearchIcon, UploadIcon } from "../icons";
import { FetchRetry } from "./FetchRetry";
import { SECTIONS, matches } from "./skills/helpers";
import { CountBadge } from "./skills/badges";
import { SkillRow } from "./skills/SkillRow";
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

/** Settings > Skills: your skills and the ones built in (Yours), and
 * Anthropic's open skills to add (Discover). Every skill is a folder with a
 * SKILL.md; switching one off stops it being offered in any conversation. */
export function SkillsTab({ active, onCreateSkill }: SkillsTabProps) {
  const { data: skills, status, error, retry } = useFetchOnActive(active, getSkills, []);
  const [view, setView] = useState<View>({ kind: "list" });
  const [tab, setTab] = useState<Tab>("yours");
  const [search, setSearch] = useState("");
  const [catalog, setCatalog] = useState<SkillPlugin[] | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [removeTarget, setRemoveTarget] = useState<SkillInfo | null>(null);
  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const addMenuRef = useRef<HTMLDivElement>(null);
  useClickOutside(addMenuRef, () => setAddMenuOpen(false), addMenuOpen);

  const loadCatalog = () => {
    setCatalogError(null);
    getSkillPlugins()
      .then(setCatalog)
      .catch((err: unknown) => setCatalogError(err instanceof Error ? err.message : "Couldn't load Discover."));
  };

  useEffect(() => {
    if (active && tab === "discover" && catalog === null) loadCatalog();
  }, [active, tab, catalog]);

  const toggle = async (skill: SkillInfo) => {
    setActionError(null);
    const result = await setSkillEnabled(skill.name, !skill.enabled);
    if ("error" in result) setActionError(result.error);
    retry();
  };

  const confirmRemove = async () => {
    if (!removeTarget) return;
    const target = removeTarget;
    setRemoveTarget(null);
    setActionError(null);
    const result = await removeSkill(target.name);
    if ("error" in result) setActionError(result.error);
    setView({ kind: "list" });
    setCatalog(null);
    retry();
  };

  const removeDialog = removeTarget && (
    <ConfirmDialog
      title={`Remove ${removeTarget.name}?`}
      description={
        removeTarget.source === "anthropic"
          ? "Its folder is deleted. You can add it again from Discover."
          : "Its folder is deleted from your skills directory. This can't be undone."
      }
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

  const detailSkill = view.kind === "detail" ? skills.find((s) => s.name === view.name) : undefined;
  if (detailSkill) {
    return (
      <>
        <SkillDetailView
          skill={detailSkill}
          onBack={() => setView({ kind: "list" })}
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
  const visible = skills.filter((s) => matches(search, s.name, s.description));
  const discover = (catalog ?? []).filter((e) => matches(search, e.title, e.description, ...e.skills));

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="mr-1 text-[22px] font-semibold">Skills</h2>
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
            aria-label="Search skills"
            className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--muted)]"
            placeholder="Search skills"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="relative" ref={addMenuRef}>
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={addMenuOpen}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-[var(--primary)] px-3.5 text-sm font-medium text-[var(--primary-fg)] hover:bg-[var(--primary-hover)]"
            onClick={() => setAddMenuOpen((v) => !v)}
          >
            <PlusIcon className="h-4 w-4" /> Add <ChevronDownIcon className="h-3.5 w-3.5" />
          </button>
          {addMenuOpen && (
            <div
              role="menu"
              className="absolute right-0 top-full z-20 mt-1 min-w-48 rounded-[10px] border border-[var(--border)] bg-[var(--panel-bg)] py-1 shadow-[var(--shadow)]"
            >
              <button
                type="button"
                role="menuitem"
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-[var(--card-bg)]"
                onClick={() => {
                  setAddMenuOpen(false);
                  setView({ kind: "upload" });
                }}
              >
                <UploadIcon className="h-3.5 w-3.5" /> Upload a skill
              </button>
              <button
                type="button"
                role="menuitem"
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-[var(--card-bg)]"
                onClick={() => {
                  setAddMenuOpen(false);
                  onCreateSkill();
                }}
              >
                <PencilIcon className="h-3.5 w-3.5" /> Create with Coscribe
              </button>
            </div>
          )}
        </div>
      </div>

      {actionError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {actionError}
        </p>
      )}

      {tab === "yours" ? (
        <>
          <FetchRetry status={status} error={error} onRetry={retry} />
          {status === "success" &&
            SECTIONS.map(({ source, title }) => {
              const rows = visible.filter((s) => s.source === source);
              if (rows.length === 0) return null;
              return (
                <section key={source}>
                  <h3 className="flex items-center gap-2 text-[17px] font-medium">
                    {title} <CountBadge count={rows.length} />
                  </h3>
                  <div className="mt-1">
                    {rows.map((skill) => (
                      <SkillRow
                        key={skill.name}
                        skill={skill}
                        onOpen={() => setView({ kind: "detail", name: skill.name })}
                        onToggle={() => toggle(skill)}
                        onRemove={() => setRemoveTarget(skill)}
                      />
                    ))}
                  </div>
                </section>
              );
            })}
          {status === "success" && visible.length === 0 && (
            <p className="py-6 text-center text-sm text-[var(--muted)]">
              {skills.length === 0 ? "No skills yet." : `No skills match "${search.trim()}".`}
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
