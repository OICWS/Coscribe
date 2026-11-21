import type { ModelRow } from "../types/settings";

/** One model the picker offers; `value` is "provider:model". */
export interface ModelChoice {
  provider: string;
  value: string;
  row: ModelRow;
}

/** The picks to remember, most recent first. */
export function rememberModel(recent: string[], value: string, keep = 8): string[] {
  return [value, ...recent.filter((v) => v !== value)].slice(0, keep);
}

/** The models the menu shows at once: the current one, then the most recently picked, then the
 * rest in order, up to `limit`; kept in their configured order so a pick doesn't reshuffle them.
 * The others go under "More models". */
export function splitChoices(choices: ModelChoice[], current: string, recent: string[], limit = 4) {
  const offered = new Set(choices.map((c) => c.value));
  const shown = new Set<string>();
  for (const value of [current, ...recent, ...choices.map((c) => c.value)]) {
    if (shown.size >= limit) break;
    if (offered.has(value)) shown.add(value);
  }
  return { top: choices.filter((c) => shown.has(c.value)), more: choices.filter((c) => !shown.has(c.value)) };
}
