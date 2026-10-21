import { useCallback, useEffect, useState } from "react";
import { artifactId, listArtifacts, readPins, writePins, type ArtifactSummary } from "../../lib/artifacts";

/** The artifacts, read when the page opens, and which of them are pinned. */
export function useArtifacts() {
  const [items, setItems] = useState<ArtifactSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pins, setPins] = useState(readPins);

  const load = useCallback(() => {
    setError(null);
    listArtifacts().then(setItems, (e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);
  useEffect(load, [load]);

  const togglePin = (item: ArtifactSummary) => {
    const next = new Set(pins);
    const id = artifactId(item);
    if (!next.delete(id)) next.add(id);
    writePins(next);
    setPins(next);
  };
  return { items, error, reload: load, pins, togglePin };
}
