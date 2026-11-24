import { useEffect, useState, type ReactNode } from "react";
import { getPluginSources, getSkillPlugins, removePluginSource, type PluginSourceRow } from "../../../lib/rest";
import type { SkillPlugin } from "../../../types/settings";
import { matches } from "./helpers";
import { AddSourceForm } from "./AddSourceForm";
import { PluginCard } from "./PluginCard";

/** Discover: Coscribe's own catalog, then the plugins of each source the person added. */
export function DiscoverPane({ search, onOpen }: { search: string; onOpen: (id: string) => void }) {
  const [catalog, setCatalog] = useState<SkillPlugin[] | null>(null);
  const [sources, setSources] = useState<PluginSourceRow[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [removeError, setRemoveError] = useState<string | null>(null);

  const load = () => {
    Promise.all([getSkillPlugins(), getPluginSources()])
      .then(([plugins, rows]) => {
        setLoadError(null);
        setCatalog(plugins);
        setSources(rows);
      })
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : "Couldn't load Discover."));
  };
  useEffect(load, []);

  const removeSource = async (repo: string) => {
    const result = await removePluginSource(repo);
    setRemoveError("error" in result ? result.error : null);
    load();
  };

  if (loadError) {
    return (
      <p className="text-sm text-[var(--danger)]">
        Couldn't load Discover: {loadError} --{" "}
        <button type="button" className="underline" onClick={load}>
          Retry
        </button>
      </p>
    );
  }
  if (catalog === null) return <p className="text-sm text-[var(--muted)]">Loading...</p>;

  const visible = catalog.filter((e) => matches(search, e.title, e.description, ...e.skills));
  const grid = (plugins: SkillPlugin[]) =>
    plugins.length === 0 ? (
      <p className="py-3 text-sm text-[var(--muted)]">{search.trim() ? `No plugins match "${search.trim()}".` : "No plugins."}</p>
    ) : (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {plugins.map((plugin) => (
          <PluginCard key={plugin.id} plugin={plugin} onOpen={() => onOpen(plugin.id)} />
        ))}
      </div>
    );

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-2">
        {grid(visible.filter((p) => p.source === null))}
        <p className="text-xs text-[var(--muted)]">
          Open-source skills from github.com/anthropics/skills and github.com/anthropics/knowledge-work-plugins (Apache License 2.0), each
          file pinned and checked before it is added.
        </p>
      </section>
      {removeError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {removeError}
        </p>
      )}
      {sources.map((source) => (
        <SourceSection key={source.repo} source={source} onRemove={() => removeSource(source.repo)}>
          {grid(visible.filter((p) => p.source === source.repo))}
        </SourceSection>
      ))}
      <AddSourceForm onAdded={load} />
    </div>
  );
}

function SourceSection({ source, onRemove, children }: { source: PluginSourceRow; onRemove: () => void; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <h3 className="min-w-0 flex-1 truncate text-[15px] font-medium">github.com/{source.repo}</h3>
        <button type="button" className="shrink-0 text-sm text-[var(--muted)] hover:text-[var(--fg)]" onClick={onRemove}>
          Remove source
        </button>
      </div>
      <p className="text-xs text-[var(--muted)]">
        Added by you and not reviewed by anyone: add a plugin from it only if you trust its authors.
        {source.elsewhere > 0 && ` ${source.elsewhere} more plugins it lists live in other repositories and aren't shown.`}
      </p>
      {children}
    </section>
  );
}
