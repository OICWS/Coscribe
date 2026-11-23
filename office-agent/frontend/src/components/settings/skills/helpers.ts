import type { InstalledPluginInfo, SkillInfo } from "../../../types/settings";

export const SOURCE_BYLINE: Record<SkillInfo["source"], string> = {
  custom: "by you",
  anthropic: "from Anthropic",
  builtin: "built into Coscribe",
};

export const SECTIONS: { source: SkillInfo["source"]; title: string }[] = [
  { source: "custom", title: "Created by you" },
  { source: "anthropic", title: "From Anthropic" },
  { source: "builtin", title: "Built into Coscribe" },
];

// Plain text worth showing in the file viewer; anything else (HTML, fonts,
// images) is listed but not opened.
export const PREVIEWABLE = new Set(["md", "txt", "py", "json", "yaml", "yml", "toml", "csv", "js", "ts", "sh", "ini", "cfg"]);

export function extension(path: string): string {
  const name = path.split("/").pop() ?? "";
  return name.includes(".") ? name.split(".").pop()!.toLowerCase() : "";
}

export function shortDate(iso: string): string {
  const date = new Date(iso);
  const sameYear = date.getFullYear() === new Date().getFullYear();
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", ...(sameYear ? {} : { year: "numeric" }) });
}

export function tabClass(active: boolean): string {
  return `-mb-px border-b-2 px-4 py-2.5 text-[15px] ${
    active ? "border-[var(--fg)] text-[var(--fg)]" : "border-transparent text-[var(--muted)] hover:text-[var(--fg)]"
  }`;
}

export function matches(query: string, ...texts: string[]): boolean {
  const q = query.trim().toLowerCase();
  return !q || texts.some((t) => t.toLowerCase().includes(q));
}

export interface FileTreeNode {
  dirs: Map<string, FileTreeNode>;
  files: string[];
}

export function buildFileTree(paths: string[]): FileTreeNode {
  const root: FileTreeNode = { dirs: new Map(), files: [] };
  for (const path of paths) {
    const parts = path.split("/");
    let node = root;
    for (const part of parts.slice(0, -1)) {
      let child = node.dirs.get(part);
      if (!child) {
        child = { dirs: new Map(), files: [] };
        node.dirs.set(part, child);
      }
      node = child;
    }
    node.files.push(parts[parts.length - 1]);
  }
  return root;
}

/** SKILL.md's YAML header is metadata, shown in the header, not the page. */
export function withoutFrontmatter(text: string): string {
  return text.replace(/^---\n[\s\S]*?\n---\n?/, "");
}

/** One row of Your plugins: a skill on its own, or a plugin standing for all its skills. */
export type ListEntry =
  | { kind: "skill"; skill: SkillInfo }
  | { kind: "plugin"; info: InstalledPluginInfo; skills: SkillInfo[]; source: SkillInfo["source"]; enabled: boolean; updated: string };

export function listEntries(skills: SkillInfo[]): ListEntry[] {
  const entries: ListEntry[] = [];
  const plugins = new Map<string, Extract<ListEntry, { kind: "plugin" }>>();
  for (const skill of skills) {
    if (!skill.plugin_info) {
      entries.push({ kind: "skill", skill });
      continue;
    }
    let entry = plugins.get(skill.plugin_info.name);
    if (!entry) {
      entry = { kind: "plugin", info: skill.plugin_info, skills: [], source: skill.source, enabled: false, updated: skill.updated };
      plugins.set(skill.plugin_info.name, entry);
      entries.push(entry);
    }
    entry.skills.push(skill);
    // On while any of its skills is; the newest skill dates it.
    entry.enabled ||= skill.enabled;
    if (skill.updated > entry.updated) entry.updated = skill.updated;
  }
  return entries;
}

export function entryMatches(query: string, entry: ListEntry): boolean {
  if (entry.kind === "skill") return matches(query, entry.skill.name, entry.skill.description);
  return matches(query, entry.info.name, entry.info.description, ...entry.skills.map((s) => s.name));
}
