/**
 * A panel of the main window (Task details, Browser, Background tasks, the
 * viewer) opened in a window of its own. The main window's page keeps the
 * conversation and its socket -- a second socket to the same conversation
 * would take its live updates -- so it sends each panel's data here, this
 * file passes it on to the panel's window, and what the user does there
 * comes back the same way.
 */

import { BrowserWindow, ipcMain, screen, type WebContents } from "electron";
import { openLinkFromApp, releaseBrowserPanelHost } from "./browserPanel";
import { titleBarWindowOptions } from "./windowChrome";

const OPEN_CHANNEL = "panel-window:open";
const FOCUS_CHANNEL = "panel-window:focus";
const LIST_CHANNEL = "panel-window:list";
const STATE_CHANNEL = "panel-window:state";
const READY_CHANNEL = "panel-window:ready";
const ACTION_CHANNEL = "panel-window:action";
const DOCK_CHANNEL = "panel-window:dock";
const PIN_CHANNEL = "panel-window:pin";
const CLOSED_EVENT = "panel-window:closed";

const PANELS = new Set(["task", "browser", "background", "viewer", "plan"]);

interface OpenRequest {
  panel: string;
  title: string;
  threadId: string;
  /** The panel's box on screen, in CSS pixels. */
  x: number;
  y: number;
  width: number;
  height: number;
}

interface PanelWindow {
  win: BrowserWindow;
  /** Closed by "Return to the main window" rather than by its close button. */
  dock: boolean;
  state: unknown;
}

const windows = new Map<string, PanelWindow>();

function panelOf(sender: WebContents): string | undefined {
  for (const [panel, entry] of windows) if (entry.win.webContents === sender) return panel;
  return undefined;
}

function finite(value: unknown, fallback: number): number {
  const n = Math.round(Number(value));
  return Number.isFinite(n) ? n : fallback;
}

function open(main: BrowserWindow, request: OpenRequest, preloadPath: string): void {
  const existing = windows.get(request.panel);
  if (existing && !existing.win.isDestroyed()) {
    existing.win.show();
    existing.win.focus();
    return;
  }
  const origin = new URL(main.webContents.getURL()).origin;
  const width = Math.max(360, finite(request.width, 480));
  const height = Math.max(320, finite(request.height, 640));
  // Where the panel was on screen, kept inside the display it is on.
  const area = screen.getDisplayNearestPoint({ x: finite(request.x, 0), y: finite(request.y, 0) }).workArea;
  const x = Math.min(Math.max(finite(request.x, area.x), area.x), area.x + area.width - width);
  const y = Math.min(Math.max(finite(request.y, area.y), area.y), area.y + area.height - height);
  const win = new BrowserWindow({
    title: request.title || "Coscribe",
    x,
    y,
    width,
    height,
    minWidth: 320,
    minHeight: 240,
    useContentSize: true,
    ...titleBarWindowOptions(),
    webPreferences: {
      preload: preloadPath,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  const entry: PanelWindow = { win, dock: false, state: existing?.state };
  windows.set(request.panel, entry);

  const query = new URLSearchParams({ panelWindow: request.panel, thread: request.threadId });
  void win.loadURL(`${origin}/?${query}`);
  win.webContents.setWindowOpenHandler(({ url }) => {
    openLinkFromApp(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (event, url) => {
    if (url.startsWith(`${origin}/`)) return;
    event.preventDefault();
    openLinkFromApp(url);
  });
  // The browser's tab views leave while the window still exists; a
  // closed window's views would go with it.
  win.on("close", () => {
    if (request.panel === "browser") releaseBrowserPanelHost(win, main);
  });
  win.on("closed", () => {
    if (windows.get(request.panel) === entry) windows.delete(request.panel);
    if (!main.isDestroyed()) main.webContents.send(CLOSED_EVENT, { panel: request.panel, dock: entry.dock });
  });
}

export function registerPanelWindowHandlers(main: BrowserWindow, preloadPath: string): void {
  ipcMain.handle(OPEN_CHANNEL, (event, request: OpenRequest) => {
    if (event.sender !== main.webContents || !PANELS.has(String(request?.panel))) return;
    open(main, { ...request, panel: String(request.panel), threadId: String(request.threadId ?? "") }, preloadPath);
  });
  ipcMain.handle(FOCUS_CHANNEL, (_event, panel: string) => {
    const win = windows.get(String(panel))?.win;
    if (!win || win.isDestroyed()) return;
    if (win.isMinimized()) win.restore();
    win.show();
    win.focus();
  });
  ipcMain.handle(LIST_CHANNEL, () => [...windows.keys()]);

  ipcMain.on(STATE_CHANNEL, (event, panel: string, state: unknown) => {
    if (event.sender !== main.webContents) return;
    const entry = windows.get(String(panel));
    if (!entry) return;
    entry.state = state;
    if (!entry.win.isDestroyed()) entry.win.webContents.send(STATE_CHANNEL, state);
  });
  // The panel's page asks once it listens; data sent before then is kept.
  ipcMain.on(READY_CHANNEL, (event) => {
    const panel = panelOf(event.sender);
    const state = panel ? windows.get(panel)?.state : undefined;
    if (state !== undefined) event.sender.send(STATE_CHANNEL, state);
  });
  ipcMain.on(ACTION_CHANNEL, (event, action: unknown) => {
    const panel = panelOf(event.sender);
    if (panel && !main.isDestroyed()) main.webContents.send(ACTION_CHANNEL, { panel, action });
  });
  ipcMain.on(DOCK_CHANNEL, (event) => {
    const panel = panelOf(event.sender);
    const entry = panel ? windows.get(panel) : undefined;
    if (!entry) return;
    entry.dock = true;
    entry.win.close();
    if (!main.isDestroyed()) {
      if (main.isMinimized()) main.restore();
      main.show();
    }
  });
  ipcMain.handle(PIN_CHANNEL, (event, pinned: boolean) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (!win || !panelOf(event.sender)) return false;
    win.setAlwaysOnTop(Boolean(pinned));
    return win.isAlwaysOnTop();
  });

  // A panel window belongs to the main window's page; a reload of that
  // page asks for the list again, a quit closes them with it.
  main.on("closed", () => {
    for (const { win } of windows.values()) if (!win.isDestroyed()) win.close();
  });
}
