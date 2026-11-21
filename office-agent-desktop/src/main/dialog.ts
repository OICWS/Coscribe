/**
 * Native OS folder picker -- ported from office-agent-desktop's (Tauri)
 * `tauri-plugin-dialog` registration and its
 * `dialog:allow-open` grant. Electron has no per-window capability/ACL
 * step to mirror here -- `ipcMain.handle` alone is the whole surface;
 * see the preload module for the contextBridge side of this.
 */

import { dialog, ipcMain, type BrowserWindow } from "electron";

// preload/index.ts duplicates this exact string rather than importing it
// from here -- a sandboxed preload (mainWindow.ts sets sandbox: true)
// can only `require` electron/events/timers/url, so any import of a
// local file crashes the whole preload's module load silently. Keep
// both copies in sync if this ever changes.
export const PICK_FOLDER_CHANNEL = "dialog:pick-folder";
export const PICK_FILE_CHANNEL = "dialog:pick-file";

export interface PickFileOptions {
  title?: string;
  filters?: { name: string; extensions: string[] }[];
}

export function registerDialogHandlers(mainWindow: BrowserWindow): void {
  ipcMain.handle(PICK_FOLDER_CHANNEL, async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ["openDirectory"],
      title: "Select a folder",
    });
    if (result.canceled || result.filePaths.length === 0) return null;
    return result.filePaths[0];
  });
  ipcMain.handle(PICK_FILE_CHANNEL, async (_event, options: PickFileOptions | undefined) => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ["openFile"],
      title: typeof options?.title === "string" ? options.title : "Select a file",
      filters: Array.isArray(options?.filters) ? options.filters : undefined,
    });
    if (result.canceled || result.filePaths.length === 0) return null;
    return result.filePaths[0];
  });
}
