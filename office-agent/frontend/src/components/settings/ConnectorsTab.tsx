import { useEffect, useRef, useState } from "react";
import {
  addMcpServer,
  bumpMcpVersion,
  getMcpCatalog,
  getMcpOAuthApps,
  getMcpServers,
  getNpmLatestVersion,
  reconnectMcpServer,
  removeMcpServer,
  setConnectorToolPolicies,
  signInMcpServer,
} from "../../lib/rest";
import type { ConnectorToolPolicy, McpCatalogEntry, McpOAuthApps, McpServersResponse } from "../../types/settings";
import { ChevronDownIcon, PlusIcon, SearchIcon } from "../icons";
import { ConnectorIcon } from "./ConnectorIcon";
import { FetchRetry } from "./FetchRetry";
import { useClickOutside } from "../../lib/useClickOutside";
import { useFetchOnActive } from "../../lib/useFetchOnActive";
import { AddCustomConnectorDialog } from "./connectors/AddCustomConnectorDialog";
import { CatalogConnectorPage } from "./connectors/CatalogConnectorPage";
import { ConnectorDetail } from "./connectors/ConnectorDetail";
import { DiscoverCard } from "./connectors/DiscoverCard";
import { buildRows, findPinnedNpmPackage } from "./connectors/helpers";
import { NoticeText } from "./connectors/NoticeText";
import { notifyPendingChanged, pendingConnectorAdds, subscribePendingChanged } from "./connectors/pending";
import { StatusCell } from "./connectors/StatusCell";
import { SIGN_IN_TEXT } from "./connectors/types";
import type { ConnectorRow, LocalServerArgs, Notice, RemoteServerArgs } from "./connectors/types";

// Header and rows share it, so each column lines up with its heading.
const ROW_GRID = "grid grid-cols-[minmax(0,1fr)_10rem_8rem] items-center gap-4 px-3";

const EMPTY: { catalog: McpCatalogEntry[]; servers: McpServersResponse; apps: McpOAuthApps } = {
  catalog: [],
  servers: {},
  apps: { saved: [], redirect_uri: "" },
};

/** Settings > Connectors: the list, a connector's own page (its tools and
 * their permissions), and adding a custom one. */
export function ConnectorsTab({ active }: { active: boolean }) {
  const [, forceRender] = useState(0);
  const [tab, setTab] = useState<"yours" | "discover">("yours");
  const [openName, setOpenName] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const addMenuRef = useRef<HTMLDivElement>(null);
  useClickOutside(addMenuRef, () => setAddMenuOpen(false), addMenuOpen);
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState<Notice | null>(null);

  useEffect(() => subscribePendingChanged(() => forceRender((n) => n + 1)), []);

  const {
    data: { catalog, servers, apps },
    status,
    retry: refresh,
  } = useFetchOnActive(
    active,
    () =>
      Promise.all([getMcpCatalog(), getMcpServers(), getMcpOAuthApps()]).then(([cat, srv, saved]) => ({
        catalog: cat,
        servers: srv,
        apps: saved,
      })),
    EMPTY,
  );

  // A slow server can finish connecting well after the tab opened, and
  // Settings has no push channel, so its live state is polled.
  const [liveServers, setLiveServers] = useState<McpServersResponse | null>(null);
  const pollLiveServers = () => {
    getMcpServers()
      .then(setLiveServers)
      .catch(() => {});
  };
  useEffect(() => {
    if (!active) return;
    setLiveServers(null);
    pollLiveServers();
    const id = setInterval(pollLiveServers, 4000);
    return () => clearInterval(id);
  }, [active]);
  const effectiveServers = liveServers ?? servers;

  const withPending = async (name: string, work: () => Promise<void>) => {
    pendingConnectorAdds.add(name);
    notifyPendingChanged();
    try {
      await work();
    } finally {
      pendingConnectorAdds.delete(name);
      notifyPendingChanged();
      refresh();
      pollLiveServers();
    }
  };

  const performAdd = (name: string, server: LocalServerArgs | RemoteServerArgs) =>
    withPending(name, async () => {
      setNotice(null);
      const result = await addMcpServer(name, server);
      const rejected = Object.values(result.rejected);
      if (rejected.length > 0) setNotice({ text: `Not added -- ${rejected[0]}`, error: true });
      else if (result.signin) setNotice({ text: SIGN_IN_TEXT, error: false, signin: { name, url: result.signin.url } });
      else if (result.connected) setNotice(null);
      else setNotice({ text: `Saved, but couldn't connect${result.error ? ` -- ${result.error}` : "."}`, error: true });
    });

  const needsSetup = (entry: McpCatalogEntry) => entry.setup !== undefined && !apps.saved.includes(entry.setup.group);

  const connectCatalog = (entry: McpCatalogEntry) => {
    setOpenName(entry.name);
    if (entry.needs_config) {
      setNotice({ text: `${entry.title ?? entry.name} needs its own token -- add it as a custom connector.`, error: false });
      return;
    }
    if (entry.setup && !apps.saved.includes(entry.setup.group)) return;
    if (entry.server_url) {
      void performAdd(entry.name, { server_url: entry.server_url, auth: entry.auth, oauth_app: entry.setup?.group });
    }
    else void performAdd(entry.name, { command: entry.command ?? "", args: entry.args ?? [] });
  };

  const signIn = (name: string) =>
    withPending(name, async () => {
      const result = await signInMcpServer(name);
      if (result.signin) setNotice({ text: SIGN_IN_TEXT, error: false, signin: { name, url: result.signin.url } });
      else if (result.connected) setNotice(null);
      else setNotice({ text: `Couldn't sign in${result.error ? ` -- ${result.error}` : "."}`, error: true });
    });

  const disconnect = async (name: string) => {
    await removeMcpServer(name);
    setOpenName(null);
    setNotice(null);
    refresh();
    pollLiveServers();
  };

  const reconnect = (name: string) =>
    withPending(name, async () => {
      const result = await reconnectMcpServer(name);
      setNotice(result.connected ? null : { text: `Still couldn't connect${result.error ? ` -- ${result.error}` : "."}`, error: true });
    });

  const checkUpdate = async (pkg: string, current: string | undefined) => {
    const result = await getNpmLatestVersion(pkg);
    if ("error" in result) setNotice({ text: `Couldn't check for updates: ${result.error}`, error: true });
    else if (result.latest === current) setNotice({ text: `Up to date (${current}).`, error: false });
    else setNotice({ text: `Version ${result.latest} is available.`, error: false, update: { pkg, version: result.latest } });
  };

  const applyUpdate = (name: string, pkg: string, version: string) =>
    withPending(name, async () => {
      const result = await bumpMcpVersion(name, pkg, version);
      setNotice(
        result.connected
          ? { text: `Updated to ${version}.`, error: false }
          : { text: `Updated, but couldn't reconnect${result.error ? ` -- ${result.error}` : "."}`, error: true },
      );
    });

  const setPolicies = async (name: string, policies: Record<string, ConnectorToolPolicy>) => {
    setLiveServers((current) => {
      const base = current ?? servers;
      const info = base[name];
      if (!info?.tools) return current;
      const tools = info.tools.map((t) => (t.name in policies ? { ...t, policy: policies[t.name] } : t));
      return { ...base, [name]: { ...info, tools } };
    });
    try {
      await setConnectorToolPolicies(name, policies);
    } catch {
      setNotice({ text: "Couldn't save the permission -- try again.", error: true });
    }
    pollLiveServers();
  };

  useEffect(() => {
    if (notice?.signin && effectiveServers[notice.signin.name]?.connected) setNotice(null);
  }, [notice, effectiveServers]);

  const rows = buildRows(catalog, effectiveServers);
  const opened = openName ? rows.find((r) => r.name === openName) : undefined;
  const backToList = () => {
    setOpenName(null);
    setNotice(null);
  };

  // Discover is the store: a connector opened there shows its store page
  // whether or not it was added; Yours opens the page that manages it.
  if (opened?.catalogEntry && (tab === "discover" || !opened.serverInfo)) {
    return (
      <CatalogConnectorPage
        entry={opened.catalogEntry}
        info={opened.serverInfo}
        pending={pendingConnectorAdds.has(opened.name)}
        notice={notice}
        appSaved={opened.catalogEntry.setup ? apps.saved.includes(opened.catalogEntry.setup.group) : true}
        redirectUri={apps.redirect_uri}
        onSetupChanged={refresh}
        onBack={backToList}
        onConnect={() => connectCatalog(opened.catalogEntry!)}
        onSignIn={() => void signIn(opened.name)}
        onManage={() => setTab("yours")}
        onDisconnect={() => void disconnect(opened.name)}
      />
    );
  }
  if (opened?.serverInfo) {
    const pinned = findPinnedNpmPackage(opened.serverInfo.args ?? []);
    return (
      <ConnectorDetail
        row={opened}
        pending={pendingConnectorAdds.has(opened.name)}
        notice={notice}
        onBack={backToList}
        onDisconnect={() => void disconnect(opened.name)}
        onReconnect={() => void reconnect(opened.name)}
        onSignIn={() => void signIn(opened.name)}
        onCheckUpdate={(pkg) => void checkUpdate(pkg, pinned?.version)}
        onApplyUpdate={(pkg, version) => void applyUpdate(opened.name, pkg, version)}
        onPolicies={(policies) => void setPolicies(opened.name, policies)}
      />
    );
  }

  const q = search.trim().toLowerCase();
  const matches = (r: ConnectorRow) => `${r.title} ${r.name} ${r.catalogEntry?.description ?? ""}`.toLowerCase().includes(q);
  const yours = rows.filter((r) => r.serverInfo !== null && (!q || matches(r)));
  const discover = rows.filter((r) => r.catalogEntry !== null && (!q || matches(r)));
  const segment = (on: boolean) =>
    `rounded-md px-3.5 py-1 text-[15px] ${
      on ? "bg-[var(--bg)] text-[var(--fg)] shadow-sm ring-1 ring-[var(--border)]" : "text-[var(--muted)] hover:text-[var(--fg)]"
    }`;
  const openRow = (name: string) => {
    setNotice(null);
    setOpenName(name);
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="mr-1 text-[22px] font-semibold">Connectors</h2>
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
            aria-label="Search connectors"
            className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--muted)]"
            placeholder="Search connectors"
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
              className="absolute right-0 top-full z-20 mt-1 min-w-52 rounded-[10px] border border-[var(--border)] bg-[var(--panel-bg)] py-1 shadow-[var(--shadow)]"
            >
              <button
                type="button"
                role="menuitem"
                className="flex w-full px-3 py-1.5 text-left text-sm hover:bg-[var(--card-bg)]"
                onClick={() => {
                  setAddMenuOpen(false);
                  setTab("discover");
                }}
              >
                Browse Discover
              </button>
              <button
                type="button"
                role="menuitem"
                className="flex w-full px-3 py-1.5 text-left text-sm hover:bg-[var(--card-bg)]"
                onClick={() => {
                  setAddMenuOpen(false);
                  setAdding(true);
                }}
              >
                Add custom connector
              </button>
            </div>
          )}
        </div>
      </div>

      {notice && <NoticeText notice={notice} />}

      <FetchRetry status={status} onRetry={refresh} />
      {tab === "yours" && status === "success" && yours.length === 0 && (
        <p className="py-6 text-center text-sm text-[var(--muted)]">
          {q ? "No connectors match." : "No connectors yet. Add one from "}
          {!q && (
            <button type="button" className="text-[var(--accent)] hover:underline" onClick={() => setTab("discover")}>
              Discover
            </button>
          )}
          {!q && "."}
        </p>
      )}
      {tab === "yours" && status === "success" && yours.length > 0 && (
        <div className="flex flex-col">
          <div className={`${ROW_GRID} border-b border-[var(--border)] pb-2 text-[13px] text-[var(--muted)]`}>
            <span>Connector</span>
            <span>Type</span>
            <span>Status</span>
          </div>
          {yours.map((row) => (
            <div key={row.name} className="border-b border-[var(--border)] py-1 last:border-b-0">
              <div
                role="button"
                tabIndex={0}
                aria-label={`Open ${row.title}`}
                className={`${ROW_GRID} cursor-pointer rounded-lg py-2 outline-none hover:bg-[var(--card-bg)] focus-visible:bg-[var(--card-bg)]`}
                onClick={() => openRow(row.name)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    openRow(row.name);
                  }
                }}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <ConnectorIcon name={row.name} title={row.title} />
                  <span className="truncate text-[15px]">{row.title}</span>
                </div>
                <div className="flex items-center text-[15px]">
                  {(row.serverInfo?.server_url ?? row.catalogEntry?.server_url) !== undefined ? "Web" : "Local"}
                  {!row.catalogEntry && (
                    <span className="ml-2 rounded-md bg-[var(--card-bg)] px-1.5 py-0.5 text-xs text-[var(--muted)]">Custom</span>
                  )}
                </div>
                <div className="flex items-center">
                  <StatusCell row={row} pending={pendingConnectorAdds.has(row.name)} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "discover" && status === "success" && (
        <div className="flex flex-col gap-4">
          <h3 className="flex items-center gap-2 text-[17px] font-medium">
            Connectors <span className="rounded-md bg-[var(--card-bg)] px-1.5 text-xs text-[var(--muted)]">{discover.length}</span>
          </h3>
          {discover.length === 0 ? (
            <p className="py-6 text-center text-sm text-[var(--muted)]">No connectors match "{search.trim()}".</p>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {discover.map((row) => (
                <DiscoverCard
                  key={row.name}
                  entry={row.catalogEntry!}
                  added={row.serverInfo !== null}
                  needsSetup={needsSetup(row.catalogEntry!)}
                  pending={pendingConnectorAdds.has(row.name)}
                  onOpen={() => openRow(row.name)}
                  onAdd={() => (needsSetup(row.catalogEntry!) ? openRow(row.name) : connectCatalog(row.catalogEntry!))}
                />
              ))}
            </div>
          )}
          <p className="text-xs text-[var(--muted)]">
            Hosted services you sign in to in your own browser: nothing to install, no app to register. Anything else can
            be added with Add &gt; Add custom connector.
          </p>
        </div>
      )}

      {adding && (
        <AddCustomConnectorDialog
          existing={rows.map((r) => r.name)}
          onClose={() => setAdding(false)}
          onAdd={(name, server) => {
            setAdding(false);
            setOpenName(name);
            void performAdd(name, server);
          }}
        />
      )}
    </div>
  );
}
