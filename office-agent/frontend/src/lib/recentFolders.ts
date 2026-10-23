import { readStored, writeStored } from "./storage";

/** Folders used lately, kept so one taken off a conversation by mistake is a click away. */
const RECENT_KEY = "coscribe.recentFolders";
const MAX_RECENT = 6;

export function folderName(path: string): string {
  const parts = path.split(/[\\/]/).filter(Boolean);
  return parts[parts.length - 1] ?? path;
}

export function readRecent(): string[] {
  try {
    const saved: unknown = JSON.parse(readStored(RECENT_KEY) ?? "[]");
    return Array.isArray(saved) ? saved.filter((p): p is string => typeof p === "string") : [];
  } catch {
    return [];
  }
}

export function remember(paths: string[]) {
  const merged = [...paths, ...readRecent().filter((p) => !paths.includes(p))];
  writeStored(RECENT_KEY, JSON.stringify(merged.slice(0, MAX_RECENT)));
}
