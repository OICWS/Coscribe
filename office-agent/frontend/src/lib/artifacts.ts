import { goToThread, startNewThread } from "./nav";
import { readStored, writeStored } from "./storage";

/** What coscribe makes that the Artifacts page lists. */
export type ArtifactKind = "slides" | "docs" | "sheets" | "dashboard";

/** One artifact as the server lists it (`GET /api/artifacts`). */
export interface ArtifactSummary {
  id: string;
  path: string;
  /** Where the file is on disk. */
  location: string;
  name: string;
  kind: ArtifactKind;
  modified_at: string;
  /** A document's heading and its opening lines. */
  excerpt: { heading: string; text: string } | null;
}

interface KindInfo {
  label: string;
  /** The kind's colour: its tile, its icon, its thumbnail's tint. */
  colour: string;
  /** What the message box starts with when "Make something new" picks this kind; null where
   * nothing can be made yet. */
  starter: string | null;
  badge: "Beta" | "Soon" | null;
}

export const KIND_ORDER: ArtifactKind[] = ["docs", "slides", "sheets", "dashboard"];

export const KINDS: Record<ArtifactKind, KindInfo> = {
  docs: { label: "Docs", colour: "var(--file-doc)", starter: "Write a document about ", badge: null },
  slides: { label: "Slides", colour: "var(--file-slides)", starter: "Make a presentation about ", badge: "Beta" },
  sheets: { label: "Sheets", colour: "var(--file-sheet)", starter: "Make a spreadsheet that ", badge: null },
  dashboard: { label: "Dashboard", colour: "var(--file-dashboard)", starter: null, badge: "Soon" },
};

async function send<T>(url: string, method: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const failure = (await response.json().catch(() => null)) as { error?: string } | null;
    throw new Error(failure?.error ?? `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

const artifactUrl = (id: string, action = "") => `/api/artifacts/${encodeURIComponent(id)}${action}`;

export const renameArtifact = (id: string, name: string) => send<ArtifactSummary>(artifactUrl(id, "/rename"), "POST", { name });
export const duplicateArtifact = (id: string) => send<ArtifactSummary>(artifactUrl(id, "/duplicate"), "POST");
export const deleteArtifact = (id: string) => send<unknown>(artifactUrl(id), "DELETE");
export const showArtifact = (id: string, reveal: boolean) => send<unknown>(artifactUrl(id, "/show"), "POST", { reveal });

/** The artifact a panel shows, or null when the file is not one coscribe made. */
export async function lookupArtifact(threadId: string, path: string): Promise<ArtifactSummary | null> {
  const response = await fetch(`/api/artifacts/lookup?thread_id=${encodeURIComponent(threadId)}&path=${encodeURIComponent(path)}`);
  return response.ok ? ((await response.json()) as ArtifactSummary) : null;
}

export async function listArtifacts(): Promise<ArtifactSummary[]> {
  const response = await fetch("/api/artifacts");
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return (await response.json()) as ArtifactSummary[];
}

export const artifactId = (item: ArtifactSummary) => item.id;

/** The first slide of a deck, drawn by the server; the time keeps a changed deck from showing stale. */
export const thumbnailUrl = (item: ArtifactSummary) => `/api/artifacts/${item.id}/thumbnail?v=${encodeURIComponent(item.modified_at)}`;

/** The conversation to show an artifact in and its path there: the one that made it while it
 * exists, else a new one in the folders that one worked in. */
async function placeOf(item: ArtifactSummary): Promise<{ thread_id: string; path: string }> {
  const response = await fetch(`/api/artifacts/${item.id}/open`, { method: "POST" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return (await response.json()) as { thread_id: string; path: string };
}

// -- Pins and layout: kept in the browser, per person, not in the deck ---------------------------

const PINS_KEY = "coscribe.pinnedArtifacts";
const LAYOUT_KEY = "coscribe.artifactsLayout";

export function readPins(): Set<string> {
  try {
    const stored: unknown = JSON.parse(readStored(PINS_KEY) ?? "[]");
    return new Set(Array.isArray(stored) ? stored.filter((id): id is string => typeof id === "string") : []);
  } catch {
    return new Set();
  }
}

export function writePins(pins: ReadonlySet<string>): void {
  writeStored(PINS_KEY, JSON.stringify([...pins]));
}

export type Layout = "grid" | "list";

export const readLayout = (): Layout => (readStored(LAYOUT_KEY) === "list" ? "list" : "grid");
export const writeLayout = (layout: Layout): void => writeStored(LAYOUT_KEY, layout);

// -- What the page shows --------------------------------------------------------------------------

export interface Filters {
  tab: "all" | "pinned";
  kind: ArtifactKind | null;
  query: string;
}

/** The artifacts to show: pinned ones first, then the newest. */
export function visibleArtifacts(items: ArtifactSummary[], pins: ReadonlySet<string>, filters: Filters): ArtifactSummary[] {
  const query = filters.query.trim().toLowerCase();
  const pinned = (item: ArtifactSummary) => pins.has(artifactId(item));
  return items
    .filter((item) => (filters.tab === "all" || pinned(item)) && (!filters.kind || item.kind === filters.kind))
    .filter((item) => !query || item.name.toLowerCase().includes(query))
    .sort((a, b) => Number(pinned(b)) - Number(pinned(a)) || b.modified_at.localeCompare(a.modified_at));
}

export function countsByKind(items: ArtifactSummary[]): Record<ArtifactKind, number> {
  const counts: Record<ArtifactKind, number> = { docs: 0, slides: 0, sheets: 0, dashboard: 0 };
  for (const item of items) counts[item.kind] += 1;
  return counts;
}

const sameDay = (a: Date, b: Date) => a.toDateString() === b.toDateString();

function dayTitle(date: Date, now: Date): string {
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (sameDay(date, now)) return "Today";
  if (sameDay(date, yesterday)) return "Yesterday";
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    ...(date.getFullYear() !== now.getFullYear() ? { year: "numeric" } : {}),
  });
}

/** The list layout's sections, in the order `visibleArtifacts` sorted them: the pinned ones, then
 * a section per day. */
export function dayGroups(items: ArtifactSummary[], pins: ReadonlySet<string>, now: Date): { title: string; items: ArtifactSummary[] }[] {
  const groups: { title: string; items: ArtifactSummary[] }[] = [];
  for (const item of items) {
    const title = pins.has(artifactId(item)) ? "Pinned" : dayTitle(new Date(item.modified_at), now);
    const last = groups[groups.length - 1];
    if (last?.title === title) last.items.push(item);
    else groups.push({ title, items: [item] });
  }
  return groups;
}

/** "Edited 9m ago", "Edited 17h ago", then the day. */
export function editedLabel(iso: string, now: Date): string {
  const date = new Date(iso);
  const minutes = Math.floor((now.getTime() - date.getTime()) / 60000);
  if (minutes < 1) return "Edited just now";
  if (minutes < 60) return `Edited ${minutes}m ago`;
  if (minutes < 24 * 60) return `Edited ${Math.floor(minutes / 60)}h ago`;
  const day = dayTitle(date, now);
  return `Edited ${day === "Yesterday" ? "yesterday" : day}`;
}

/** What the page does with an artifact or a kind: `showFile` shows a file in its panel and
 * `setComposerText` fills the message box of the conversation that starts. */
export function artifactActions(showFile: (threadId: string, path: string) => void, setComposerText: (text: string) => void) {
  return {
    /** Opens it in a conversation, with the file in its panel. */
    open: (item: ArtifactSummary) => {
      // A file that has gone since the list was read has nothing to open; the next visit drops it.
      placeOf(item).then(
        (place) => {
          showFile(place.thread_id, place.path);
          goToThread(place.thread_id);
        },
        () => undefined,
      );
    },
    /** A new conversation, its message box started for the kind. */
    make: (kind: ArtifactKind) => {
      startNewThread();
      setComposerText(KINDS[kind].starter ?? "");
    },
  };
}
