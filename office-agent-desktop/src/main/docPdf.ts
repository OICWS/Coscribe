/**
 * A Doc's PDF without a printer: the page that asked is printed by Chromium itself, to A4. The
 * renderer has made the page print-only (its own `@media print` rules) before it asks and saves
 * the bytes it gets back, as it saves a Word export; this side only prints.
 */

import { ipcMain } from "electron";

// preload/index.ts duplicates this string (a sandboxed preload cannot import it).
export const DOC_PDF_CHANNEL = "doc:print-to-pdf";

const MARGIN_INCHES = 0.7;

export function registerDocPdfHandlers(): void {
  ipcMain.handle(DOC_PDF_CHANNEL, (event): Promise<Buffer> =>
    event.sender.printToPDF({
      pageSize: "A4",
      printBackground: true,
      margins: { top: MARGIN_INCHES, bottom: MARGIN_INCHES, left: MARGIN_INCHES, right: MARGIN_INCHES },
    }),
  );
}
