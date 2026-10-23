/** What an attached file looks like to the person: an image and a PDF can be
 * seen, anything else is a name and a type. */
export type AttachmentView =
  | { kind: "image"; name: string; src: string }
  | { kind: "pdf"; name: string; path: string }
  | { kind: "file"; name: string; path: string };

/** The line that tells the model which workspace files a message came with. The server takes it back
 * off a replayed message and gives the page the paths (`split_attached_files`). */
export function attachedFilesNote(paths: string[]): string {
  return `(Attached files, now in the workspace: ${paths.join(", ")})`;
}

const FILES_NOTE = /\n*\(Attached files, now in the workspace: ([\s\S]+)\)\s*$/;

/** A message's text without the note naming its files, and the files' paths. */
export function splitAttachedFiles(text: string): { text: string; files: string[] } {
  const found = FILES_NOTE.exec(text);
  if (!found) return { text, files: [] };
  return { text: text.slice(0, found.index), files: found[1].split(", ").filter(Boolean) };
}

export function attachmentKind(name: string): "pdf" | "file" {
  return name.toLowerCase().endsWith(".pdf") ? "pdf" : "file";
}
