import { useState } from "react";
import { readStored, writeStored } from "./storage";

/** Everything the bar can hold; the person pins some and the rest wait in its menu. */
export const TOOLBAR_ITEMS = ["sidebar", "artifacts", "task", "plan", "browser", "background"] as const;
export type ToolbarItem = (typeof TOOLBAR_ITEMS)[number];

/** Panels belong to one conversation, so outside it only the other items are offered. */
export const CONVERSATION_ITEMS: readonly ToolbarItem[] = ["task", "plan", "browser", "background"];

/** The sidebar already links to Artifacts, so that one starts in the menu. */
export const DEFAULT_PINNED: readonly ToolbarItem[] = ["sidebar", "task", "plan", "browser", "background"];

const KEY = "coscribe.toolbar.pinned";

/** Items the person cannot unpin: without the sidebar button a hidden sidebar cannot come back. */
export const ALWAYS_PINNED: readonly ToolbarItem[] = ["sidebar"];

/** What the browser remembered, without anything this version does not know; the defaults when it
 * remembered nothing usable. A stored empty list is a choice and stays empty, except for the
 * items that are always pinned. */
export function normalizePinned(raw: string | null): ToolbarItem[] {
  try {
    const stored: unknown = raw === null ? null : JSON.parse(raw);
    if (Array.isArray(stored)) return TOOLBAR_ITEMS.filter((item) => ALWAYS_PINNED.includes(item) || stored.includes(item));
  } catch {
    // Unreadable: the defaults.
  }
  return [...DEFAULT_PINNED];
}

const readPinned = () => normalizePinned(readStored(KEY));

const writePinned = (items: readonly ToolbarItem[]) => writeStored(KEY, JSON.stringify(items));

/** The pinned items, kept in the browser as they change. */
export function usePinnedItems(): [ToolbarItem[], (items: ToolbarItem[]) => void] {
  const [pinned, setPinned] = useState(readPinned);
  return [
    pinned,
    (items) => {
      setPinned(items);
      writePinned(items);
    },
  ];
}
