/** A panel opened in a window of its own (office-agent-desktop's
 * main/panelWindows.ts). The main window owns the conversation and its
 * socket, so it sends each panel's data across, and the panel's window
 * sends back what the user does there. */

import type { CommentLink } from "./slideComments";
import { useCallback, useEffect, useRef, useState } from "react";
import type { BrowserCapture } from "./browserCapture";
import type { ScheduledRun, ScheduledTask } from "../types/settings";
import type { PanelId, Rect } from "./dockLayout";
import { PANEL_IDS } from "./dockLayout";
import { isElectron } from "./electron";
import type { ProgressItem } from "./workflowProgress";

export type PanelWindowState =
  | {
      panel: "task";
      threadId: string;
      title: string;
      task: ScheduledTask | null;
      run: ScheduledRun | null;
      workflowSteps: ProgressItem[] | null;
      refreshSignal: string;
      busy: boolean;
      canSaveAsWorkflow: boolean;
    }
  | { panel: "browser"; threadId: string }
  | { panel: "background"; threadId: string; refreshKey: number; focusTaskId: string | null }
  | { panel: "viewer"; threadId: string; path: string | null; refreshKey: string };

export type PanelWindowAction =
  | { type: "openTask"; task: ScheduledTask }
  | { type: "saveAsWorkflow" }
  | { type: "view"; path: string }
  | { type: "sendToChat"; capture: BrowserCapture }
  | { type: "sendComment"; text: string; link?: CommentLink }
  | { type: "stopAgent" }
  | { type: "approve"; id: string; approved: boolean; scope?: "task" };

/** The panel this page shows on its own, when it is a panel's window. */
export const PANEL_WINDOW: PanelId | null = (() => {
  const panel = new URLSearchParams(window.location.search).get("panelWindow");
  return PANEL_IDS.includes(panel as PanelId) ? (panel as PanelId) : null;
})();

export function canOpenPanelWindows(): boolean {
  return isElectron() && typeof window.coscribeDesktop.openPanelWindow === "function";
}

async function openPanelWindow(request: {
  panel: PanelId;
  title: string;
  threadId: string;
  x: number;
  y: number;
  width: number;
  height: number;
}): Promise<void> {
  await window.coscribeDesktop.openPanelWindow?.(request);
}

export function focusPanelWindow(panel: PanelId): void {
  void window.coscribeDesktop?.focusPanelWindow?.(panel);
}

async function listPanelWindows(): Promise<PanelId[]> {
  if (!canOpenPanelWindows()) return [];
  const panels = (await window.coscribeDesktop.listPanelWindows?.()) ?? [];
  return panels.filter((p): p is PanelId => PANEL_IDS.includes(p as PanelId));
}

function sendPanelWindowState(state: PanelWindowState): void {
  window.coscribeDesktop?.sendPanelWindowState?.(state.panel, state);
}

function onPanelWindowAction(callback: (panel: PanelId, action: PanelWindowAction) => void): () => void {
  if (!canOpenPanelWindows()) return () => {};
  return (
    window.coscribeDesktop.onPanelWindowAction?.((payload) => {
      const { panel, action } = payload as { panel: PanelId; action: PanelWindowAction };
      callback(panel, action);
    }) ?? (() => {})
  );
}

/** `dock`: closed by "Return to the main window", else by its close button. */
function onPanelWindowClosed(callback: (panel: PanelId, dock: boolean) => void): () => void {
  if (!canOpenPanelWindows()) return () => {};
  return (
    window.coscribeDesktop.onPanelWindowClosed?.((payload) => {
      const { panel, dock } = payload as { panel: PanelId; dock: boolean };
      callback(panel, dock);
    }) ?? (() => {})
  );
}

export function onPanelWindowState(callback: (state: PanelWindowState) => void): () => void {
  return window.coscribeDesktop?.onPanelWindowState?.((payload) => callback(payload as PanelWindowState)) ?? (() => {});
}

export function sendPanelWindowAction(action: PanelWindowAction): void {
  window.coscribeDesktop?.sendPanelWindowAction?.(action);
}

export function dockPanelWindow(): void {
  window.coscribeDesktop?.dockPanelWindow?.();
}

export async function setPanelWindowPinned(pinned: boolean): Promise<boolean> {
  return (await window.coscribeDesktop?.setPanelWindowPinned?.(pinned)) ?? false;
}

export function setTitleBarHeight(height: number): void {
  window.coscribeDesktop?.setTitleBarHeight?.(height);
}

/** The main window's side: which panels are in windows of their own, and
 * keeping each one's data current there. `states` is what each panel
 * would show now; the handlers' latest versions are used. */
export function usePanelWindows({
  states,
  titles,
  threadId,
  onAction,
  onClosed,
}: {
  states: Record<PanelId, PanelWindowState>;
  titles: Record<PanelId, string>;
  threadId: string;
  onAction: (action: PanelWindowAction) => void;
  onClosed: (panel: PanelId, dock: boolean) => void;
}) {
  const [poppedOut, setPoppedOut] = useState<PanelId[]>([]);
  const handlers = useRef({ onAction, onClosed });
  handlers.current = { onAction, onClosed };
  const sent = useRef(new Map<PanelId, string>());

  useEffect(() => {
    void listPanelWindows().then((panels) => setPoppedOut((current) => [...new Set([...current, ...panels])]));
    const stopAction = onPanelWindowAction((_panel, action) => handlers.current.onAction(action));
    const stopClosed = onPanelWindowClosed((panel, dock) => {
      sent.current.delete(panel);
      setPoppedOut((current) => current.filter((p) => p !== panel));
      handlers.current.onClosed(panel, dock);
    });
    return () => {
      stopAction();
      stopClosed();
    };
  }, []);

  useEffect(() => {
    for (const panel of poppedOut) {
      const json = JSON.stringify(states[panel]);
      if (sent.current.get(panel) === json) continue;
      sent.current.set(panel, json);
      sendPanelWindowState(states[panel]);
    }
  });

  const popOut = useCallback(
    (panel: PanelId, rect: Rect) => {
      sent.current.delete(panel);
      setPoppedOut((current) => (current.includes(panel) ? current : [...current, panel]));
      void openPanelWindow({
        panel,
        title: titles[panel],
        threadId,
        x: window.screenX + rect.x,
        y: window.screenY + rect.y,
        width: rect.w,
        height: rect.h,
      });
    },
    [titles, threadId],
  );

  return { poppedOut, popOut };
}
