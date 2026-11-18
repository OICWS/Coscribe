import { useState } from "react";
import { addProvider, getProviders, getProvidersCatalog, removeProvider } from "../../lib/rest";
import { useFetchOnActive } from "../../lib/useFetchOnActive";
import type { ProviderCatalogEntry, ProvidersResponse } from "../../types/settings";
import { ConfirmDialog } from "../ConfirmDialog";
import { FetchRetry } from "./FetchRetry";
import { DiscoverGrid } from "./providers/DiscoverGrid";
import { ProviderPage, type ProviderForm, type ProviderStatus } from "./providers/ProviderPage";
import { ProvidersHeader, type ProvidersView } from "./providers/ProvidersHeader";
import { YoursList, type ProviderRow } from "./providers/YoursList";
import { findEntry, formProblem } from "./providers/catalog";

const EMPTY: { catalog: ProviderCatalogEntry[]; configured: ProvidersResponse } = { catalog: [], configured: {} };

const loadProviders = () =>
  Promise.all([getProvidersCatalog(), getProviders()]).then(([catalog, configured]) => ({ catalog, configured }));

/** The open page: a provider by its name, or the form for a new custom one. */
type Opened = { name: string } | "custom" | null;

/** Settings > Providers: the providers added (Yours), the ones Coscribe knows
 * (Discover), and a provider's own page with its key and default model. */
export function ProvidersTab({ active }: { active: boolean }) {
  const { data, status: loadStatus, error: loadError, retry: refresh } = useFetchOnActive(active, loadProviders, EMPTY);
  const { catalog, configured } = data;
  const [chosenView, setView] = useState<ProvidersView | null>(null);
  const [opened, setOpened] = useState<Opened>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<ProviderStatus>(null);
  const [removeTarget, setRemoveTarget] = useState<string | null>(null);

  const view = chosenView ?? (Object.keys(configured).length > 0 ? "yours" : "discover");
  const configuredName = (name: string) => Object.keys(configured).find((n) => n.toLowerCase() === name.toLowerCase());
  const open = (next: Opened) => {
    setStatus(null);
    setOpened(next);
  };

  const save = async (form: ProviderForm): Promise<boolean> => {
    const problem = formProblem(form, catalog);
    if (problem) {
      setStatus({ text: problem, error: true });
      return false;
    }
    const name = form.name.trim();
    try {
      const result = await addProvider(name, form.baseUrl.trim(), form.apiKey.trim(), form.defaultModel.trim());
      const rejected = Object.values(result.rejected);
      if (rejected.length > 0) {
        setStatus({ text: `Not saved -- ${rejected[0]}`, error: true });
        return false;
      }
      setStatus({ text: result.restart_required ? "Saved. Restart coscribe-web to apply." : "Saved.", error: false });
    } catch (err) {
      setStatus({ text: err instanceof Error ? err.message : "Not saved.", error: true });
      return false;
    }
    setOpened({ name });
    refresh();
    return true;
  };

  const confirmRemove = async () => {
    if (!removeTarget) return;
    const name = removeTarget;
    setRemoveTarget(null);
    try {
      await removeProvider(name);
      setOpened(null);
    } catch (err) {
      setStatus({ text: err instanceof Error ? err.message : `Couldn't remove ${name}.`, error: true });
    }
    refresh();
  };

  const removeDialog = removeTarget && (
    <ConfirmDialog
      title="Remove provider?"
      description={`"${removeTarget}" and its stored API key will be removed. Any thread or workflow still using it will fail until you add it again.`}
      onCancel={() => setRemoveTarget(null)}
      onConfirm={confirmRemove}
    />
  );

  if (opened) {
    const name = opened === "custom" ? null : opened.name;
    const entry = name ? findEntry(catalog, name) : null;
    const added = name ? configuredName(name) : undefined;
    return (
      <>
        <ProviderPage
          key={name ?? "custom"}
          entry={entry}
          name={entry ? null : name}
          info={added ? configured[added] : null}
          status={status}
          onBack={() => open(null)}
          onSave={save}
          onRemove={() => added && setRemoveTarget(added)}
        />
        {removeDialog}
      </>
    );
  }

  const q = search.trim().toLowerCase();
  const matches = (text: string) => !q || text.toLowerCase().includes(q);
  const rows: ProviderRow[] = Object.entries(configured).map(([name, info]) => {
    const entry = findEntry(catalog, name);
    return { name, title: entry?.title ?? name, entry, info };
  });
  return (
    <div className="flex flex-col gap-5">
      <ProvidersHeader view={view} onView={setView} search={search} onSearch={setSearch} onAddCustom={() => open("custom")} />
      <FetchRetry status={loadStatus} error={loadError} onRetry={refresh} />
      {loadStatus === "success" && view === "yours" && (
        <YoursList
          rows={rows.filter((r) => matches(`${r.title} ${r.name} ${r.info.default_model}`))}
          searching={q !== ""}
          onOpen={(n) => open({ name: n })}
          onDiscover={() => setView("discover")}
        />
      )}
      {loadStatus === "success" && view === "discover" && (
        <DiscoverGrid
          entries={catalog.filter((e) => matches(`${e.title} ${e.name} ${e.description}`))}
          added={(e) => configuredName(e.name) !== undefined}
          search={search}
          onOpen={(n) => open({ name: n })}
        />
      )}
      {removeDialog}
    </div>
  );
}
