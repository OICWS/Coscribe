import { useEffect, useState } from "react";
import { EMPTY, isArrangement, type Arrangement, type Hint } from "./dockArrangement";
import { isDockNode, PANEL_IDS, type PanelId } from "./dockLayout";

const STORAGE_KEY = "coscribe.panelLayout";

export interface DockState {
  arrangement: Arrangement;
  /** Where each closed panel sat, to put it back there. */
  hints: Partial<Record<PanelId, Hint>>;
}

function isHint(value: unknown): value is Hint {
  if (!value || typeof value !== "object") return false;
  const h = value as Record<string, unknown>;
  if ("target" in h) return PANEL_IDS.includes(h.target as PanelId) && ["left", "right", "top", "bottom"].includes(h.edge as string);
  return (h.side === "left" || h.side === "right") && typeof h.index === "number" && typeof h.width === "number" && h.width > 0;
}

function readHints(raw: unknown): DockState["hints"] {
  const hints: DockState["hints"] = {};
  if (!raw || typeof raw !== "object") return hints;
  for (const [id, hint] of Object.entries(raw as Record<string, unknown>)) {
    if (PANEL_IDS.includes(id as PanelId) && isHint(hint)) hints[id as PanelId] = hint;
  }
  return hints;
}

function load(): DockState {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as Record<string, unknown> | null;
    if (raw && isArrangement(raw.arrangement)) return { arrangement: raw.arrangement, hints: readHints(raw.hints) };
    // The earlier format: one block of panels right of the conversation.
    if (raw && isDockNode(raw.tree) && typeof raw.width === "number" && raw.width > 0) {
      return { arrangement: { left: [], right: [{ tree: raw.tree, width: raw.width }] }, hints: {} };
    }
  } catch {
    // Unreadable or blocked storage: start from nothing.
  }
  return { arrangement: EMPTY, hints: {} };
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
