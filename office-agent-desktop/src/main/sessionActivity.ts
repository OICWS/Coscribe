/**
 * What the page tells the shell about the conversation it shows: whether a turn is running
 * (the computer is kept awake for it) and when coscribe needs the person (the taskbar button
 * flashes, if the window is not in front). Both follow Sessions settings in `.env`, read fresh
 * each time like the other desktop settings.
 */

import { ipcMain, powerMonitor, powerSaveBlocker } from "electron";
import { getMainWindow } from "./mainWindow";
import { flashOnAttention, keepAwake, keepAwakeOnBattery } from "./sidecar";

// Keep these in sync with the preload's own copies -- a sandboxed preload cannot import them.
const SET_BUSY_CHANNEL = "session:set-busy";
const ATTENTION_CHANNEL = "session:attention";

// A setting changed in the middle of a long turn takes effect within this long.
const RECHECK_MS = 30_000;

let busy = false;
let blockerId: number | null = null;
let recheck: NodeJS.Timeout | null = null;

function shouldStayAwake(): boolean {
  return busy && keepAwake() && (!powerMonitor.isOnBatteryPower() || keepAwakeOnBattery());
}

function applyAwake(): void {
  const want = shouldStayAwake();
  if (want && blockerId === null) {
    blockerId = powerSaveBlocker.start("prevent-app-suspension");
  } else if (!want && blockerId !== null) {
    powerSaveBlocker.stop(blockerId);
    blockerId = null;
  }
  if (busy && recheck === null) recheck = setInterval(applyAwake, RECHECK_MS);
  if (!busy && recheck !== null) {
    clearInterval(recheck);
    recheck = null;
  }
}

/** Flashes the taskbar button until the window is focused. */
export function requestAttention(): void {
  const win = getMainWindow();
  if (!win || win.isDestroyed() || win.isFocused() || !flashOnAttention()) return;
  win.flashFrame(true);
  win.once("focus", () => win.flashFrame(false));
}

export function registerSessionActivityHandlers(): void {
  ipcMain.on(SET_BUSY_CHANNEL, (_event, value: unknown) => {
    busy = value === true;
    applyAwake();
  });
  ipcMain.on(ATTENTION_CHANNEL, requestAttention);
  powerMonitor.on("on-battery", applyAwake);
  powerMonitor.on("on-ac", applyAwake);
}
