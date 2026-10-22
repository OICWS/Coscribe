import { useCallback, useState } from "react";
import type { ArtifactKind } from "./artifacts";

/** The kind a conversation started from the Artifacts page is to make, until its first message goes. */
export function useArtifactStart(threadId: string) {
  const [made, setMade] = useState<{ thread: string; kind: ArtifactKind } | null>(null);
  const kind = made?.thread === threadId ? made.kind : null;
  const start = useCallback((thread: string, started: ArtifactKind) => setMade({ thread, kind: started }), []);
  const clear = useCallback(() => setMade(null), []);
  /** The kind to send with a message, once: not for a slash command, and not for what cannot be made yet. */
  const take = (text: string): Exclude<ArtifactKind, "dashboard"> | undefined => {
    if (!kind || kind === "dashboard" || text.trimStart().startsWith("/")) return undefined;
    setMade(null);
    return kind;
  };
  return { kind, start, clear, take };
}
