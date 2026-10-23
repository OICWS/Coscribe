interface Call {
  toolName: string;
  result?: unknown;
  isError?: boolean;
}

export interface SavedSystem {
  id: string;
  name: string;
  summary: string;
}

/** The design systems a run of calls saved, each once (a later save of the same id wins): the card
 * at the end of a turn points at what it made. A call that failed or still waits has nothing to show. */
export function savedSystems(calls: Iterable<Call>): SavedSystem[] {
  const found = new Map<string, SavedSystem>();
  for (const call of calls) {
    if (call.toolName !== "save_design_system" || call.result === undefined || call.isError) continue;
    let parsed = call.result;
    if (typeof parsed === "string") {
      try {
        parsed = JSON.parse(parsed);
      } catch {
        continue;
      }
    }
    const { id, name, summary } = (parsed ?? {}) as Partial<SavedSystem>;
    if (typeof id === "string" && typeof name === "string") found.set(id, { id, name, summary: typeof summary === "string" ? summary : "" });
  }
  return [...found.values()];
}
