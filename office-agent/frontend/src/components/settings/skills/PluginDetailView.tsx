import { useEffect, useMemo, useState } from "react";
import { addSkillPlugin, getMcpCatalog, getSkillPlugin, getSkillPluginFile } from "../../../lib/rest";
import type { McpCatalogEntry, SkillPluginDetail } from "../../../types/settings";
import { ArrowLeftIcon, CheckIcon } from "../../icons";
import { ConnectorIcon } from "../ConnectorIcon";
import { shortDate, buildFileTree, connectorTitle } from "./helpers";
import { SkillBadge } from "./badges";
import { FileTreeView } from "./FileTree";
import { FileViewer } from "./FileViewer";
import type { PluginTab } from "./types";

export function PluginDetailView({
  id,
  onBack,
  onAdded,
}: {
  id: string;
  onBack: () => void;
  onAdded: () => void;
}) {
  const [plugin, setPlugin] = useState<SkillPluginDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tab, setTab] = useState<PluginTab>("overview");
  const [selected, setSelected] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<McpCatalogEntry[]>([]);

  const load = () => {
    getSkillPlugin(id)
      .then((detail) => {
        setPlugin(detail);
        setSelected((prev) => prev ?? (detail.files.find((f) => f.endsWith("/SKILL.md")) ?? detail.files[0] ?? null));
      })
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : "Couldn't load this plugin."));
  };
  useEffect(load, [id]);
  useEffect(() => {
    getMcpCatalog()
      .then(setCatalog)
      .catch(() => {});
  }, []);

  const tree = useMemo(() => buildFileTree(plugin?.files ?? []), [plugin]);
  const tabClass = (active: boolean) =>
    `-mb-px border-b-2 px-4 py-2.5 text-[15px] ${
      active ? "border-[var(--fg)] text-[var(--fg)]" : "border-transparent text-[var(--muted)] hover:text-[var(--fg)]"
    }`;
  const tabButton = (value: PluginTab, label: string, count?: number) => (
    <button type="button" className={tabClass(tab === value)} onClick={() => setTab(value)}>
      {label}
      {count !== undefined && <span className="text-[var(--muted)]"> &middot; {count}</span>}
    </button>
  );

  const add = async () => {
    setAdding(true);
    setAddError(null);
    const result = await addSkillPlugin(id);
    setAdding(false);
    if ("error" in result) setAddError(result.error);
    load();
    onAdded();
  };

  const back = (
    <button type="button" className="flex w-fit items-center gap-2 text-[15px] text-[var(--fg)] hover:opacity-70" onClick={onBack}>
      <ArrowLeftIcon className="h-4 w-4" /> Discover
    </button>
  );
  if (!plugin) {
    return (
      <div className="flex flex-col gap-5">
        {back}
        <p className="text-sm text-[var(--muted)]">{loadError ?? "Loading..."}</p>
      </div>
    );
  }
  const complete = plugin.added === plugin.skills.length;

  return (
    <div className="flex h-full min-h-0 flex-col gap-5">
      {back}
      <div className="flex items-center gap-4">
        <SkillBadge large />
        <div className="min-w-0 flex-1">
          <div className="truncate text-lg font-semibold">{plugin.title}</div>
          <div className="text-sm text-[var(--muted)]">
            by {plugin.author}
            {plugin.version && <> &middot; v{plugin.version}</>} &middot; {plugin.skills.length} skills &middot; updated{" "}
            {shortDate(plugin.updated)}
          </div>
        </div>
        {complete ? (
          <span className="flex shrink-0 items-center gap-1 px-3 text-sm text-[var(--muted)]">
            <CheckIcon className="h-4 w-4" /> Added
          </span>
        ) : (
          <button
            type="button"
            disabled={adding}
            className="shrink-0 rounded-lg bg-[var(--primary)] px-4 py-1.5 text-sm font-medium text-[var(--primary-fg)] hover:bg-[var(--primary-hover)] disabled:opacity-60"
            onClick={add}
          >
            {adding ? "Adding..." : plugin.added > 0 ? "Add the rest" : "Add"}
          </button>
        )}
      </div>
      {addError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {addError}
        </p>
      )}
      <div className="flex border-b border-[var(--border)]">
        {tabButton("overview", "Overview")}
        {tabButton("contents", "Contents", plugin.files.length)}
        {tabButton("skills", "Skills", plugin.skills.length)}
        {tabButton("connectors", "Connectors", plugin.connectors.length)}
      </div>

      {tab === "overview" && (
        <div className="flex flex-col gap-4">
          <p className="text-[15px] leading-relaxed">{plugin.description}</p>
          <p className="text-sm text-[var(--muted)]">
            From github.com/{plugin.repo}, under the {plugin.license === "Apache-2.0" ? "Apache License 2.0" : plugin.license}.
            Adding it downloads {plugin.skills.length} skills into your skills folder; you can look through every file first
            under Contents.
          </p>
        </div>
      )}

      {tab === "contents" && (
        <div className="flex min-h-[420px] flex-1 overflow-hidden rounded-xl border border-[var(--border)]">
          <div className="w-60 shrink-0 overflow-y-auto border-r border-[var(--border)] bg-[var(--card-bg)]/40 p-2">
            <FileTreeView
              node={tree}
              prefix=""
              depth={0}
              selectedPath={selected}
              collapsed={collapsed}
              onToggleDir={(path) =>
                setCollapsed((prev) => {
                  const next = new Set(prev);
                  if (next.has(path)) next.delete(path);
                  else next.add(path);
                  return next;
                })
              }
              onSelectFile={setSelected}
            />
          </div>
          {selected ? (
            <FileViewer source={plugin.id} path={selected} load={(path) => getSkillPluginFile(plugin.id, path)} />
          ) : (
            <p className="p-5 text-sm text-[var(--muted)]">No files.</p>
          )}
        </div>
      )}

      {tab === "skills" && (
        <div>
          {plugin.skill_details.map((skill) => (
            <button
              key={skill.name}
              type="button"
              className="flex w-full flex-col gap-0.5 border-b border-[var(--border)] py-3.5 text-left last:border-b-0 hover:opacity-80"
              onClick={() => {
                setSelected(plugin.files.find((f) => f.endsWith(`${skill.name}/SKILL.md`)) ?? null);
                setTab("contents");
              }}
            >
              <span className="text-[15px]">{skill.name}</span>
              <span className="line-clamp-2 text-sm text-[var(--muted)]">{skill.description}</span>
            </button>
          ))}
        </div>
      )}

      {tab === "connectors" && (
        <div>
          {plugin.connectors.length === 0 ? (
            <p className="py-6 text-center text-sm text-[var(--muted)]">This plugin doesn't use any connectors.</p>
          ) : (
            <>
              <p className="pb-2 text-sm text-[var(--muted)]">
                Services these skills work with. The ones coscribe has a connector for can be added under Connectors.
              </p>
              {plugin.connectors.map((c) => {
                const entry = catalog.find((e) => e.name === c.connector);
                return (
                  <div key={c.name} className="flex items-center gap-4 border-b border-[var(--border)] py-3.5 last:border-b-0">
                    <ConnectorIcon name={c.connector ?? c.name} title={entry?.title ?? connectorTitle(c.name)} size="md" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[15px]">{entry?.title ?? connectorTitle(c.name)}</div>
                      {entry && <div className="truncate text-sm text-[var(--muted)]">{entry.description}</div>}
                    </div>
                    <span className="shrink-0 text-sm text-[var(--muted)]">{c.connector ? "In coscribe" : "Not in coscribe yet"}</span>
                  </div>
                );
              })}
            </>
          )}
        </div>
      )}
    </div>
  );
}
