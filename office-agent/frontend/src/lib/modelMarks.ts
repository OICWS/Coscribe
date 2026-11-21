import type { ModelRow } from "../types/settings";

/** 1048576 -> "1M", 128000 -> "128K": a context window as people quote it. */
export function contextLabel(tokens: number): string {
  if (tokens >= 1_000_000) return `${Number((tokens / 1_000_000).toFixed(1))}M`;
  if (tokens >= 1_000) return `${Math.round(tokens / 1_000)}K`;
  return String(tokens);
}

const INPUT_LABELS: Record<string, string> = { image: "Vision", pdf: "PDF", audio: "Audio", video: "Video" };
const OUTPUT_LABELS: Record<string, string> = { image: "Image", audio: "Audio", video: "Video" };

/** The modalities as card labels, in the catalog's order; one the labels don't know keeps its name. */
export const inputCards = (row: ModelRow) => row.inputs.map((m) => INPUT_LABELS[m] ?? m);
export const outputCards = (row: ModelRow) => row.outputs.map((m) => OUTPUT_LABELS[m] ?? m);

/** The plain lines under the cards: effort levels, context window, and no tool calls. */
export function modelFacts(row: ModelRow): string[] {
  const facts: string[] = [];
  if (row.effort_levels.length > 0) facts.push(`Effort: ${row.effort_levels.join(" · ")}`);
  if (row.context) facts.push(`${contextLabel(row.context)} context`);
  if (!row.tools) facts.push("No tool calls");
  return facts;
}

/** A row for a model the server hasn't described: one saved but no longer listed. */
export function typedModelRow(id: string): ModelRow {
  return { id, name: id, inputs: [], outputs: [], effort_levels: [], context: null, tools: false, kind: "chat", known: false };
}
