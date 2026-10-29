import { createContext } from "react";

interface Call {
  toolName: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  isError?: boolean;
}

/** A page of a deck being built, as written so far; `version` counts its writes, so a rewritten page
 * is fetched again. */
export interface DraftPage {
  path: string;
  version: number;
}

const folderOf = (path: string) => path.replace(/[^\\/]*$/, "");

/** The slide pages a run has written so far: the `.svg` files of the folder written to last, in file
 * name order, which is the order of the slides. The deck itself comes only when they are built, so
 * until then these are all there is to show. */
export function draftPages(entries: Iterable<Call | { kind: string }>): DraftPage[] {
  const writes = new Map<string, number>();
  let latest = "";
  for (const call of entries) {
    if (!("toolName" in call)) continue;
    const path = call.arguments.path;
    if (call.result === undefined || call.isError || typeof path !== "string" || !/\.svg$/i.test(path)) continue;
    if (/^(read|list|inspect|get|check|render|preview|search|find|describe|count)_/.test(call.toolName)) continue;
    writes.set(path, (writes.get(path) ?? 0) + 1);
    latest = folderOf(path);
  }
  return [...writes]
    .filter(([path]) => folderOf(path) === latest)
    .map(([path, version]) => ({ path, version }))
    .sort((a, b) => a.path.localeCompare(b.path, undefined, { numeric: true }));
}

/** The pages written so far, for the panel of a deck that is not built yet. */
export const DraftPages = createContext<DraftPage[]>([]);
