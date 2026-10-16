import { useEffect, useState } from "react";
import { isDockNode, PANEL_IDS, type DockNode, type PanelId, type PlaceHint } from "./dockLayout";

const STORAGE_KEY = "coscribe.panelLayout";

export interface DockState {
  tree: DockNode | null;
  /** The panels' share of the window, in pixels, beside the conversation. */
  width: number;
  /** Where each closed panel sat, to put it back there. */
  hints: Partial<Record<PanelId, PlaceHint>>;
}

function readHints(raw: unknown): DockState["hints"] {
  const hints: DockState["hints"] = {};
  if (!raw || typeof raw !== "object") return hints;
  for (const [id, hint] of Object.entries(raw as Record<string, unknown>)) {
    const h = hint as Partial<PlaceHint> | null;
    if (
      PANEL_IDS.includes(id as PanelId) &&
      h &&
      PANEL_IDS.includes(h.target as PanelId) &&
      ["left", "right", "top", "bottom"].includes(h.edge as string)
    ) {
      hints[id as PanelId] = h as PlaceHint;
    }
  }
  return hints;
}

function load(): DockState {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as unknown;
    if (raw && typeof raw === "object") {
      const { tree, width, hints } = raw as Record<string, unknown>;
      if ((tree === null || isDockNode(tree)) && typeof width === "number" && width > 0) {
        return { tree: tree as DockNode | null, width, hints: readHints(hints) };
      }
    }
  } catch {
    // Unreadable or blocked storage: start from nothing.
  }
  return { tree: null, width: 0, hints: {} };
}

/** The panel arrangement, remembered on this computer across conversations. */
export function useDockLayout() {
  const [state, setState] = useState<DockState>(load);
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Not remembered this time; the layout still works.
    }
  }, [state]);
  return [state, setState] as const;
}
