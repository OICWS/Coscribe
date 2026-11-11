import type { ActivityFile } from "../types/session";
import { editedLabel, type ArtifactKind } from "./artifacts";
import { baseName, canvasOfPage, kindOfFile } from "./fileMentions";
import { isDocMarkdown, isViewable } from "./viewers";

/** What the conversation made, as the notices above the message box show it: something that
 * opens in its panel, pictures, or a file that opens in its own program. */
export type MadeOutput =
  | { kind: "artifact"; artifact: ArtifactKind; file: ActivityFile }
  | { kind: "images"; files: ActivityFile[] }
  | { kind: "external"; type: string; file: ActivityFile };

const IMAGE = /\.(png|jpe?g|gif|webp|bmp|svg)$/i;

const EXTERNAL: [RegExp, string][] = [
  [/\.(xlsx?|xlsm)$/i, "Excel"],
  [/\.docx?$/i, "Word"],
  [/\.pdf$/i, "PDF"],
  [/\.(csv|tsv)$/i, "CSV"],
  [/\.ppt$/i, "PowerPoint"],
];

export const isImageFile = (path: string) => IMAGE.test(path);

/** The program a file opens in, or null for one the notices leave out (code, notes, data). */
export function externalType(path: string): string | null {
  return EXTERNAL.find(([pattern]) => pattern.test(path))?.[1] ?? null;
}

/** The made files the notices offer, newest first. A Markdown file counts as a document only once
 * the server said it is a Doc (`docs`); a design's pages are the one design they belong to; the
 * pictures are one notice, so a reply that saves ten charts doesn't push everything else away. */
export function madeOutputs(outputs: ActivityFile[], docs: ReadonlySet<string>): MadeOutput[] {
  const made: MadeOutput[] = [];
  const seen = new Set<string>();
  const images: ActivityFile[] = [];
  let imagesAt = -1;
  for (const file of outputs) {
    if (!file.exists) continue;
    const path = canvasOfPage(file.path) ?? file.path;
    if (seen.has(path)) continue;
    seen.add(path);
    if (isImageFile(path)) {
      if (imagesAt < 0) imagesAt = made.length;
      images.push(file);
    } else if (isViewable(path)) {
      if (isDocMarkdown(path) && !docs.has(path)) continue;
      made.push({ kind: "artifact", artifact: kindOfFile(path), file: path === file.path ? file : { ...file, path, name: baseName(path) } });
    } else {
      const type = externalType(path);
      if (type && file.openable) made.push({ kind: "external", type, file });
    }
  }
  if (images.length > 0) made.splice(imagesAt, 0, { kind: "images", files: images });
  return made;
}

/** When a file last changed, as a notice says it: "just now", "5m ago", "Nov 9". */
export function changedWhen(iso: string | null, now: Date): string {
  if (!iso) return "";
  return editedLabel(iso, now).replace(/^Edited /, "");
}

/** The folder a file is in, as the person reads it; "" for the top of the workspace. */
export function folderOf(path: string): string {
  const cut = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
  return cut > 0 ? path.slice(0, cut) : "";
}

/** A file's name as a title: no extension, and a design canvas without its `.design.json`. */
export const titleOf = (name: string) => name.replace(/\.design\.json$/i, "").replace(/\.[^.]+$/, "");

/** What closing a notice remembers: the file as it is now, so a later change brings it back. */
export const closeKey = (threadId: string, file: ActivityFile) => `${threadId}\u0000${file.path}\u0000${file.modified_at ?? ""}`;
