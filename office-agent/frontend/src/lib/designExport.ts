import { designFileUrl } from "./artifacts";
import { saveBlob } from "./slides";

export type DesignExport = "html" | "pdf";

const stemOf = (path: string) => (path.split(/[\\/]/).pop() ?? path).replace(/\.html?$/i, "");

/** The page as the person asked for it: the HTML file itself, or a PDF made through the system's
 * print dialog. */
export async function exportDesign(threadId: string, path: string, version: string, kind: DesignExport): Promise<void> {
  if (kind === "html") {
    const response = await fetch(designFileUrl(threadId, path, version));
    if (!response.ok) throw new Error("The design could not be read");
    saveBlob(await response.blob(), `${stemOf(path)}.html`);
    return;
  }
  await printDesign(threadId, path, version);
}

/** The page loaded again in a hidden frame of its own, which prints itself when told to: "Save as
 * PDF" in the dialog makes the file. The frame is sandboxed like the panel's, with the right to
 * open the dialog added, and the app's own page stays out of the print. */
function printDesign(threadId: string, path: string, version: string): Promise<void> {
  const frame = document.createElement("iframe");
  frame.setAttribute("aria-hidden", "true");
  frame.setAttribute("sandbox", "allow-scripts allow-modals");
  frame.style.cssText = "position:fixed;left:-10000px;top:0;width:1100px;height:800px;border:0";
  frame.src = `${designFileUrl(threadId, path, version)}&print=true`;
  return new Promise<void>((done, fail) => {
    const finish = () => {
      window.removeEventListener("message", onMessage);
      clearTimeout(timer);
      frame.remove();
    };
    const onMessage = (e: MessageEvent) => {
      if (e.source !== frame.contentWindow || e.data !== "coscribe-printed") return;
      finish();
      done();
    };
    const timer = setTimeout(() => {
      finish();
      fail(new Error("The design could not be prepared for printing"));
    }, 120_000);
    window.addEventListener("message", onMessage);
    frame.addEventListener("load", () => frame.contentWindow?.postMessage("coscribe-print", "*"), { once: true });
    document.body.appendChild(frame);
  });
}
