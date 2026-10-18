import { useEffect, useState } from "react";
import { getDesignSystem } from "../../lib/slideEditing";
import type { DesignSystem } from "../../lib/slideText";

/** The deck's palette, fonts and text styles, read once for the properties panel; null until
 * they are, or for a deck that has none. */
export function useDesignSystem(threadId: string, path: string): DesignSystem | null {
  const [found, setFound] = useState<{ key: string; design: DesignSystem } | null>(null);
  const key = `${threadId}\n${path}`;
  useEffect(() => {
    let live = true;
    getDesignSystem(threadId, path).then(
      (design) => live && setFound({ key, design }),
      () => undefined,
    );
    return () => {
      live = false;
    };
  }, [threadId, path, key]);
  return found?.key === key ? found.design : null;
}
