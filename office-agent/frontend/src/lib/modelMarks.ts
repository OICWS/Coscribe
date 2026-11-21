import type { ModelRow } from "../types/settings";

/** 1048576 -> "1M", 128000 -> "128K": a context window as people quote it. */
export function contextLabel(tokens: number): string {
  if (tokens >= 1_000_000) return `${Number((tokens / 1_000_000).toFixed(1))}M`;
  if (tokens >= 1_000) return `${Math.round(tokens / 1_000)}K`;
  return String(tokens);
}

/** What a model can do, one line each, for the tip shown on hover. A model the catalog doesn't
 * list says only that, since anything else would be a guess. */
export function modelMarks(row: ModelRow): string[] {
  if (!row.known) return ["Not in the bundled catalog: what it can do is unknown"];
  const marks: string[] = [];
  if (row.vision) marks.push("Reads images");
  if (row.effort_levels.length > 0) marks.push(`Effort: ${row.effort_levels.join(", ")}`);
  if (row.context) marks.push(`${contextLabel(row.context)} context`);
  if (!row.tools) marks.push("No tool calls");
  return marks;
}

/** A row for a model the server hasn't described: one saved but no longer listed. */
export function typedModelRow(id: string): ModelRow {
  return { id, name: id, vision: false, effort_levels: [], context: null, tools: false, kind: "chat", known: false };
}
