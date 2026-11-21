import type { StateEvent } from "../types/wire";

export type Effort = StateEvent["effort"];

/** The scale a choice is kept on, so it carries over a model switch (runtime_lg/effort.py). */
export const EFFORT_SCALE: readonly Effort[] = ["low", "medium", "high", "extra", "max", "ultra"];

const SCALE_LABELS: Record<Effort, string> = { low: "Low", medium: "Medium", high: "High", extra: "Extra", max: "Max", ultra: "Ultra" };
const MODEL_LABELS: Record<string, string> = { low: "Low", medium: "Medium", high: "High", xhigh: "Extra high", max: "Max" };
const RANK: Record<string, number> = { low: 0, medium: 1, high: 2, extra: 3, xhigh: 3, max: 4, ultra: 5 };

export interface EffortStop {
  /** What picking it sends. */
  value: Effort;
  label: string;
}

/** A model's own level as the scale value that runs as it. */
const toScale = (level: string): Effort => (level === "xhigh" ? "extra" : (level as Effort));

/** The level a choice runs as on a model with these levels: the nearest at or below it, else the
 * lowest, as the server does. */
export function levelFor(effort: Effort, levels: readonly string[]): string {
  const below = levels.filter((level) => RANK[level] <= RANK[effort]);
  return below.length > 0 ? below[below.length - 1] : levels[0];
}

/** The stops the picker offers: the model's own levels with their names, or the whole scale
 * when the model's levels are not known. */
export function effortStops(levels: readonly string[] | null): EffortStop[] {
  if (!levels || levels.length === 0) return EFFORT_SCALE.map((value) => ({ value, label: SCALE_LABELS[value] }));
  return levels.map((level) => ({ value: toScale(level), label: MODEL_LABELS[level] ?? level }));
}

/** Which stop is showing for a choice. */
export function stopIndex(effort: Effort, levels: readonly string[] | null): number {
  if (!levels || levels.length === 0) return EFFORT_SCALE.indexOf(effort);
  return levels.indexOf(levelFor(effort, levels));
}
