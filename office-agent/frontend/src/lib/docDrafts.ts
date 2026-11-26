import type { DocDraftEvent, DocDraftFinishedEvent } from "../types/wire";

export type LiveDoc = DocDraftEvent & { committed?: boolean };
export type LiveDocs = Record<string, LiveDoc>;

export function updateDocDraft(current: LiveDocs, event: DocDraftEvent | DocDraftFinishedEvent): LiveDocs {
  if (event.type === "doc_draft") return { ...current, [event.path]: event };
  const draft = current[event.path];
  if (draft?.id !== event.id) return current;
  const next = { ...current };
  if (event.committed) next[event.path] = { ...draft, committed: true };
  else delete next[event.path];
  return next;
}
