import type { LogItem } from "./reducer";

/** A note added while a reply was being worked on; part of that turn, not a turn of its own.
 * Pending until the model reads it. */
export interface SteerItem {
  id: string;
  kind: "steer";
  text: string;
  status: "pending" | "delivered";
  images?: string[];
  files?: string[];
  /** What the model gets when it differs from `text` (the note naming the attached files, an
   * element picked in a preview); only on a note sent from this page. */
  outgoingText?: string;
}

export type NewSteer = Omit<SteerItem, "kind" | "status">;

export function pendingSteer({ type: _type, ...note }: NewSteer & { type: string }): SteerItem {
  return { ...note, kind: "steer", status: "pending" };
}

/** The notes a turn ended before reading, as the message they are sent as: as this page shows
 * them, attachments as cards. Another tab only has the server's text. */
export function requeuedNotes(items: LogItem[], ids: string[], text: string): { text: string; images?: string[]; files?: string[] } {
  const notes = items.filter((item): item is SteerItem => item.kind === "steer" && ids.includes(item.id));
  if (notes.length !== ids.length) return { text };
  const images = notes.flatMap((note) => note.images ?? []);
  const files = notes.flatMap((note) => note.files ?? []);
  return {
    text: notes.map((note) => note.text).join("\n\n"),
    ...(images.length > 0 ? { images } : {}),
    ...(files.length > 0 ? { files } : {}),
  };
}
