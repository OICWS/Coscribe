import type { MemoryEntry } from "../types/workflow";

// What a task remembers between runs (decision 0034), as a person reads and edits it: a list one
// item per line, everything else as written.

export const MEMORY_TYPE_LABEL: Record<MemoryEntry["type"], string> = {
  text: "Text",
  number: "Number",
  date: "Date",
  list: "List",
};

function itemText(item: unknown): string {
  return typeof item === "string" ? item : JSON.stringify(item);
}

/** The value as text to edit: a list one item per line. */
export function memoryText(value: unknown, type: MemoryEntry["type"]): string {
  if (value === null || value === undefined) return "";
  if (type === "list" && Array.isArray(value)) return value.map(itemText).join("\n");
  return typeof value === "string" ? value : JSON.stringify(value);
}

/** What edited text keeps; null forgets the value. An item that reads as JSON stays an object. */
export function memoryFromText(text: string, type: MemoryEntry["type"]): unknown {
  const trimmed = text.trim();
  if (!trimmed) return null;
  if (type === "number") return Number.isFinite(Number(trimmed)) ? Number(trimmed) : trimmed;
  if (type !== "list") return trimmed;
  return trimmed
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      if (!/^[[{]/.test(line)) return line;
      try {
        return JSON.parse(line) as unknown;
      } catch {
        return line;
      }
    });
}

const PREVIEW_ITEMS = 3;

/** One line for the task page: "12 items: a, b, c, …". */
export function memoryPreview(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Nothing yet";
  if (Array.isArray(value)) {
    if (value.length === 0) return "No items yet";
    const shown = value.slice(0, PREVIEW_ITEMS).map(itemText).join(", ");
    const more = value.length > PREVIEW_ITEMS ? ", …" : "";
    return `${value.length} ${value.length === 1 ? "item" : "items"}: ${shown}${more}`;
  }
  return itemText(value);
}

/** Who kept the value: a person, or a run that finished. */
export function keptBy(by: string): string {
  return by === "you" ? "set by you" : "kept by a run";
}
