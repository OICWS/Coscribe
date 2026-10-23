import { useCallback, useEffect, useState } from "react";
import { listArtifacts, type PageItem } from "../../lib/artifacts";
import { listSystemItems } from "../../lib/designSystemItems";
import { usePins } from "./usePins";

/** The artifacts, read when the page opens, and which of them are pinned. */
export function useArtifacts() {
  const [items, setItems] = useState<PageItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { pins, toggle } = usePins();

  const load = useCallback(() => {
    setError(null);
    // The library is read beside the files; one that cannot be read leaves the files showing.
    Promise.all([listArtifacts(), listSystemItems().catch(() => [])]).then(
      ([files, systems]) => setItems([...files, ...systems]),
      (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
    );
  }, []);
  useEffect(load, [load]);

  return { items, error, reload: load, pins, togglePin: (item: PageItem) => toggle(item.id) };
}
