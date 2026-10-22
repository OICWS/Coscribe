import { getDocBlocks } from "./docsEditor";
import { blocksToMarkdown } from "./docsMarkdown";
import { getDocxBytes } from "./docxReview";
import { saveBlob } from "./slides";

export type DocsExport = "word" | "pdf" | "markdown";

const DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
const stemOf = (path: string) => (path.split(/[\\/]/).pop() ?? path).replace(/\.docx$/i, "");

/** The document as the person asked for it: the Word file itself, Markdown written from its blocks,
 * or a PDF made through the system's print dialog from the page layout the viewer draws. */
export async function exportDocument(threadId: string, path: string, kind: DocsExport): Promise<void> {
  const stem = stemOf(path);
  if (kind === "word") saveBlob(new Blob([await getDocxBytes(threadId, path, "final")], { type: DOCX_TYPE }), `${stem}.docx`);
  else if (kind === "markdown") {
    const { blocks } = await getDocBlocks(threadId, path);
    saveBlob(new Blob([blocksToMarkdown(blocks)], { type: "text/markdown;charset=utf-8" }), `${stem}.md`);
  } else await printDocument(await getDocxBytes(threadId, path, "final"), stem);
}

/** The document drawn page by page in a hidden frame, which is handed to the print dialog: "Save as
 * PDF" there makes the file. A frame of its own keeps the app's page out of the print. */
async function printDocument(bytes: ArrayBuffer, title: string): Promise<void> {
  const frame = document.createElement("iframe");
  frame.setAttribute("aria-hidden", "true");
  frame.style.cssText = "position:fixed;left:-10000px;top:0;width:1100px;height:800px;border:0";
  document.body.appendChild(frame);
  try {
    const page = frame.contentDocument;
    if (!page || !frame.contentWindow) throw new Error("The document could not be prepared for printing");
    page.title = title;
    page.head.insertAdjacentHTML("beforeend", "<style>@page{margin:0}body{margin:0}.docx-wrapper{background:none!important;padding:0!important}.docx-wrapper>section.docx{box-shadow:none!important;margin:0!important}</style>");
    const docx = await import("docx-preview");
    await docx.renderAsync(bytes, page.body, page.head, { className: "docx", inWrapper: true, experimental: true });
    await page.fonts.ready;
    await new Promise<void>((done) => {
      frame.contentWindow?.addEventListener("afterprint", () => done(), { once: true });
      frame.contentWindow?.print();
      setTimeout(done, 120_000);
    });
  } finally {
    frame.remove();
  }
}
