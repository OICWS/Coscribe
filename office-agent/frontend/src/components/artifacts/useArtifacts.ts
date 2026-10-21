import { useCallback, useEffect, useState } from "react";
import { listArtifacts, type ArtifactSummary } from "../../lib/artifacts";
import { usePins } from "./usePins";

/** The artifacts, read when the page opens, and which of them are pinned. */
export function useArtifacts() {
  const [items, setItems] = useState<ArtifactSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { pins, toggle } = usePins();

  const load = useCallback(() => {
    setError(null);
    listArtifacts().then(setItems, (e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);
  useEffect(load, [load]);

  return { items, error, reload: load, pins, togglePin: (item: ArtifactSummary) => toggle(item.id) };
}
