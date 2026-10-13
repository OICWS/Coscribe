import type { SkillInfo } from "../../../types/settings";

export const SOURCE_BYLINE: Record<SkillInfo["source"], string> = {
  custom: "by you",
  anthropic: "from Anthropic",
  builtin: "built into coscribe",
};

export const SECTIONS: { source: SkillInfo["source"]; title: string }[] = [
  { source: "custom", title: "Created by you" },
  { source: "anthropic", title: "From Anthropic" },
  { source: "builtin", title: "Built into coscribe" },
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

const CONNECTOR_TITLES: Record<string, string> = {
  hubspot: "HubSpot",
  bigquery: "BigQuery",
  docusign: "DocuSign",
  zoominfo: "ZoomInfo",
  "otter-ai": "Otter.ai",
  "microsoft-365": "Microsoft 365",
  "amplitude-eu": "Amplitude (EU)",
  gmail: "Gmail",
  similarweb: "Similarweb",
};

export function connectorTitle(name: string): string {
  return CONNECTOR_TITLES[name] ?? name.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
