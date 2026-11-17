import { useEffect, useState } from "react";
import { goToThread, startNewThread } from "../../lib/nav";
import { getEnvironments } from "../../lib/rest";
import { listSessions, timeAgo, type SessionTab } from "../../lib/sessionList";
import { threadLabel } from "../../lib/threadStatus";
import type { ThreadSummary } from "../../types/session";
import { DEFAULT_ENVIRONMENT } from "../EnvironmentDialog";
import { SearchIcon } from "../icons";

const TABS: { value: SessionTab; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "archived", label: "Archived" },
];

const toolButton = "flex h-9 w-9 items-center justify-center rounded-lg text-[var(--fg)] hover:bg-[var(--card-bg)]";

/** Every session as one list, opened from the sidebar's "View all": its title, the environment it
 * works in and when it last changed. */
export function SessionsPage({ threads }: { threads: ThreadSummary[] }) {
  const [tab, setTab] = useState<SessionTab>("active");
  const [searching, setSearching] = useState(false);
  const [query, setQuery] = useState("");
  const [names, setNames] = useState<Record<string, string>>({});
  // Re-rendered each minute so "8 minutes ago" keeps counting while the page stays open.
  const [now, setNow] = useState(Date.now);

  useEffect(() => {
    getEnvironments()
      .then(({ environments }) => setNames(Object.fromEntries(environments.map((e) => [e.id, e.name]))))
      .catch(() => undefined);
    const timer = window.setInterval(() => setNow(Date.now()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  const environmentName = (id: string) => names[id] ?? (id === DEFAULT_ENVIRONMENT ? "Default" : id);
  const shown = listSessions(threads, tab, query, environmentName);
  const closeSearch = () => {
    setSearching(false);
    setQuery("");
  };

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-[1180px] px-8 pb-16 pt-6">
        <h1 className="text-[34px] font-normal leading-tight" style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}>
          Sessions
        </h1>
        <div className="mt-6 flex items-center justify-between gap-4">
          <div role="tablist" className="flex gap-1">
            {TABS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={tab === value}
                className={`rounded-lg px-3 py-1.5 text-[15px] ${tab === value ? "bg-[var(--card-bg)] text-[var(--fg)]" : "text-[var(--muted)] hover:text-[var(--fg)]"}`}
                onClick={() => setTab(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            {searching && (
              <input
                autoFocus
                aria-label="Search sessions"
                placeholder="Search sessions"
                value={query}
                className="h-9 w-56 rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-3 text-sm outline-none focus:border-[var(--focus)]"
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Escape" && closeSearch()}
              />
            )}
            <button
              type="button"
              title="Search"
              aria-label="Search"
              aria-pressed={searching}
              className={toolButton}
              onClick={() => (searching ? closeSearch() : setSearching(true))}
            >
              <SearchIcon className="h-[18px] w-[18px]" />
            </button>
            <button
              type="button"
              className="h-9 rounded-lg bg-[var(--primary)] px-3 text-[15px] font-medium text-[var(--primary-fg)] hover:opacity-90"
              onClick={startNewThread}
            >
              New session
            </button>
          </div>
        </div>
        <div className="mt-6" role="list" aria-label="Sessions">
          {shown.length === 0 && (
            <p className="px-1 py-6 text-sm text-[var(--muted)]">
              {query.trim() ? "No sessions match the search." : tab === "archived" ? "Nothing archived." : "No sessions yet."}
            </p>
          )}
          {shown.map((thread) => (
            <SessionRow key={thread.thread_id} thread={thread} environment={environmentName(thread.environment)} now={now} />
          ))}
        </div>
      </div>
    </div>
  );
}

function SessionRow({ thread, environment, now }: { thread: ThreadSummary; environment: string; now: number }) {
  const title = threadLabel(thread);
  return (
    <button
      type="button"
      role="listitem"
      data-testid="session-row"
      className="grid w-full grid-cols-[minmax(0,1fr)_5rem_5rem_6rem] items-center gap-2 border-b border-[var(--border)] px-1 py-4 text-left last:border-b-0 hover:bg-[var(--card-bg)] sm:grid-cols-[minmax(0,1fr)_9rem_9rem_8rem] sm:gap-4"
      onClick={() => goToThread(thread.thread_id)}
    >
      <span className="min-w-0 truncate text-[15px]" title={title}>{title}</span>
      <span className="min-w-0 truncate text-[13px] text-[var(--muted)]" title={thread.group ?? undefined}>{thread.group}</span>
      <span className="min-w-0 truncate text-[13px] text-[var(--muted)]" title={environment}>{environment}</span>
      <span className="min-w-0 truncate text-right text-[15px] text-[var(--muted)]">{timeAgo(thread.updated_at, now)}</span>
    </button>
  );
}
