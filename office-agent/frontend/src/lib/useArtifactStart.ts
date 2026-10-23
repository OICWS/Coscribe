import { useCallback, useState } from "react";
import type { PageKind } from "./artifacts";

interface Started {
  thread: string;
  kind: PageKind;
  /** The library design system a Slides conversation is to follow, by id. */
  designSystem: string | null;
}

/** The kind a conversation started from the Artifacts page is to make, until its first message goes. */
export function useArtifactStart(threadId: string) {
  const [made, setMade] = useState<Started | null>(null);
  const here = made?.thread === threadId ? made : null;
  const kind = here?.kind ?? null;
  const designSystem = here?.designSystem ?? null;
  const start = useCallback((thread: string, started: PageKind) => setMade({ thread, kind: started, designSystem: null }), []);
  const clear = useCallback(() => setMade(null), []);
  const chooseDesignSystem = useCallback((id: string | null) => setMade((current) => (current ? { ...current, designSystem: id } : current)), []);
  /** The fields to send with a message, once: not for a slash command, and not for what cannot be made yet. */
  const take = (text: string): { artifact?: Exclude<PageKind, "dashboard">; design_system?: string } => {
    if (!kind || kind === "dashboard" || text.trimStart().startsWith("/")) return {};
    setMade(null);
    return kind === "slides" && designSystem ? { artifact: kind, design_system: designSystem } : { artifact: kind };
  };
  return { kind, designSystem, start, clear, chooseDesignSystem, take };
}
