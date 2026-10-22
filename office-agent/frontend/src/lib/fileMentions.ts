import type { ArtifactKind } from "./artifacts";
import { isDocx } from "./docxReview";
import { isPptx } from "./slides";
import { isViewable } from "./viewers";

interface Call {
  toolName: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  isError?: boolean;
}

/** The decks and documents a run of calls made or changed: a finished call on a file the viewer
 * shows that is not a read (an approved call carries its result too), each path once, in the order
 * it was first touched. */
export function touchedFiles(calls: Iterable<Call>): string[] {
  const paths = new Set<string>();
  for (const call of calls) {
    const path = call.arguments.path;
    if (call.result !== undefined && !call.isError && typeof path === "string" && isViewable(path) && !call.toolName.startsWith("read_")) paths.add(path);
  }
  return [...paths];
}

export const baseName = (path: string) => path.split(/[\\/]/).pop() ?? path;

/** The artifact kind a file belongs to, for its icon and its words. */
export const kindOfFile = (path: string): ArtifactKind => (isPptx(path) ? "slides" : isDocx(path) ? "docs" : "sheets");

export const KIND_WORDS: Record<ArtifactKind, string> = { docs: "Document", slides: "Presentation", sheets: "Spreadsheet", dashboard: "Dashboard" };

/** The files this conversation made or changed, by their file names, for turning a mention in a
 * reply into a chip. Two files with one name keep the later. */
export function filesByName(calls: Iterable<Call>): Map<string, string> {
  return new Map(touchedFiles(calls).map((path) => [baseName(path), path]));
}

/** What a mention's link carries, so the renderer can tell it from a web link. */
export const FILE_LINK = "coscribe-file:";

/** The path in a mention's link. The markdown pipeline percent-encodes what is not ASCII in a link,
 * so a file named in Chinese arrives as `%E6%96...`. */
export function fileLinkPath(href: string): string {
  const path = href.slice(FILE_LINK.length);
  try {
    return decodeURIComponent(path);
  } catch {
    return path;
  }
}

interface Node {
  type: string;
  value?: string;
  url?: string;
  children?: Node[];
}

const escapeForPattern = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** A remark plugin: a known file's name in running text or in backticks becomes a link the renderer
 * draws as a chip. Names inside links and code blocks are left alone. */
export function remarkFileChips(files: ReadonlyMap<string, string>) {
  const names = [...files.keys()].sort((a, b) => b.length - a.length);
  const pattern = names.length ? new RegExp(`(?<![\\w./\\\\-])(${names.map(escapeForPattern).join("|")})(?![\\w-])`, "g") : null;
  const link = (name: string): Node => ({ type: "link", url: FILE_LINK + (files.get(name) ?? name), children: [{ type: "text", value: name }] });
  const walk = (node: Node) => {
    if (!node.children || ["link", "linkReference", "code", "definition"].includes(node.type)) return;
    node.children = node.children.flatMap((child): Node[] => {
      if (child.type === "inlineCode" && child.value && files.has(child.value.trim())) return [link(child.value.trim())];
      if (child.type !== "text" || !child.value || !pattern) {
        walk(child);
        return [child];
      }
      const parts: Node[] = [];
      let from = 0;
      for (const match of child.value.matchAll(pattern)) {
        if (match.index > from) parts.push({ type: "text", value: child.value.slice(from, match.index) });
        parts.push(link(match[1]));
        from = match.index + match[1].length;
      }
      if (!parts.length) return [child];
      if (from < child.value.length) parts.push({ type: "text", value: child.value.slice(from) });
      return parts;
    });
  };
  return () => (tree: Node) => {
    if (pattern || files.size) walk(tree);
  };
}
