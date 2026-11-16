import { threadLabel } from "./threadStatus";

export type SessionTab = "active" | "archived";

interface Listed {
  thread_id: string;
  preview: string;
  updated_at: string | null;
  archived: boolean;
  environment: string;
}

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 365 * 24 * 3600],
  ["month", 30 * 24 * 3600],
  ["week", 7 * 24 * 3600],
  ["day", 24 * 3600],
  ["hour", 3600],
  ["minute", 60],
];

const relative = new Intl.RelativeTimeFormat("en", { numeric: "always" });

/** "8 minutes ago", the way the Sessions page says when a session last changed. */
export function timeAgo(iso: string | null, now = Date.now()): string {
  if (!iso) return "";
  const seconds = Math.max(0, Math.round((now - Date.parse(iso)) / 1000));
  if (Number.isNaN(seconds)) return "";
  for (const [unit, size] of UNITS) {
    if (seconds >= size) return relative.format(-Math.floor(seconds / size), unit);
  }
  return "just now";
}

/** The sessions one tab shows, newest first, narrowed by the search text
 * (a title or an environment's name). */
export function listSessions<T extends Listed>(
  threads: T[],
  tab: SessionTab,
  query: string,
  environmentName: (id: string) => string,
): T[] {
  const text = query.trim().toLowerCase();
  return threads
    .filter((t) => t.archived === (tab === "archived"))
    .filter(
      (t) =>
        !text ||
        threadLabel(t).toLowerCase().includes(text) ||
        environmentName(t.environment).toLowerCase().includes(text),
    )
    .sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""));
}
