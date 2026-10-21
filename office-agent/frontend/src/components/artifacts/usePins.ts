import { useState } from "react";
import { readPins, writePins } from "../../lib/artifacts";

/** The pinned artifacts' ids, kept in the browser. */
export function usePins() {
  const [pins, setPins] = useState(readPins);
  const toggle = (id: string) => {
    const next = new Set(pins);
    if (!next.delete(id)) next.add(id);
    writePins(next);
    setPins(next);
  };
  return { pins, toggle };
}
