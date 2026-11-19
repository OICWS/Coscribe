import { createContext } from "react";

interface Call {
  toolName: string;
  status?: string;
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

/** Only a live build identifies which source pages belong to the requested deck. */
export function draftPages(entries: (Call | { kind: string })[], deck: string): DraftPage[] {
  const normalize = (path: string) => path.replaceAll("\\", "/").replace(/^\.\//, "");
  const build = [...entries].reverse().find((call) => "toolName" in call
    && call.toolName === "build_pptx_from_pages"
    && typeof call.arguments.path === "string" && normalize(call.arguments.path) === normalize(deck));
  if (!build || !("toolName" in build) || build.result !== undefined
      || (build.status && build.status !== "approved") || typeof build.arguments.pages_dir !== "string") return [];
  const folder = normalize(build.arguments.pages_dir).replace(/\/$/, "");
  const writes = new Map<string, number>();
  for (const call of entries) {
    if (!("toolName" in call)) continue;
    const path = call.arguments.path;
    if (call.result === undefined || call.isError || typeof path !== "string" || !/\.svg$/i.test(path)) continue;
    if (/^(read|list|inspect|get|check|render|preview|search|find|describe|count)_/.test(call.toolName)) continue;
    if (folderOf(normalize(path)).replace(/\/$/, "") === (folder === "." ? "" : folder)) {
      writes.set(path, (writes.get(path) ?? 0) + 1);
    }
  }
  return [...writes]
    .map(([path, version]) => ({ path, version }))
    .sort((a, b) => a.path.localeCompare(b.path, undefined, { numeric: true }));
}

/** The pages written so far, for the panel of a deck that is not built yet. */
export const DraftPages = createContext<DraftPage[]>([]);
