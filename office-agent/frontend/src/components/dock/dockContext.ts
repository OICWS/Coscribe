import { createContext, useContext, type PointerEvent, type ReactNode } from "react";
import type { PanelId } from "../../lib/dockLayout";

/** What a panel inside PanelDock gets: its header is the drag handle, and
 * `controls` (expand with its Move menu, and close) go at its right end. */
export interface DockPanelApi {
  id: PanelId | null;
  headerProps: {
    onPointerDown: (e: PointerEvent<HTMLElement>) => void;
    onDoubleClick: (e: React.MouseEvent<HTMLElement>) => void;
  };
  controls: ReactNode;
  /** A panel is being dragged or the Move menu is open: page content drawn
   * by the OS above the window (the desktop browser) must step aside. */
  frozen: boolean;
  /** Another panel fills the window, so this one is out of sight. */
  hidden: boolean;
  /** Changes whenever the panel's box moves or resizes. */
  boundsKey: string;
}

const noop = () => {};

const OUTSIDE_DOCK: DockPanelApi = {
  id: null,
  headerProps: { onPointerDown: noop, onDoubleClick: noop },
  controls: null,
  frozen: false,
  hidden: false,
  boundsKey: "",
};

export const DockPanelContext = createContext<DockPanelApi>(OUTSIDE_DOCK);

export function useDockPanel(): DockPanelApi {
  return useContext(DockPanelContext);
}
