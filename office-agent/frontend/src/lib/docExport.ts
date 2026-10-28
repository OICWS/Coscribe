import { getDoc } from "./docFile";
import { canPrintToPdf, printToPdf } from "./electron";
import { saveBlob } from "./slides";

export type DocExportKind = "markdown" | "word" | "pdf";

const DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
const stemOf = (path: string) => (path.split(/[\\/]/).pop() ?? path).replace(/\.md$/i, "");

/** The Doc as the person asked for it: its Markdown without the front matter, a Word file the server
 * makes, or a PDF the desktop app prints itself, or in a browser the system's print dialog from the page as it is on screen. */
export async function exportDoc(threadId: string, path: string, kind: DocExportKind): Promise<void> {
  const stem = stemOf(path);
  if (kind === "markdown") {
    const { blocks } = await getDoc(threadId, path);
    saveBlob(new Blob([`${blocks.map((b) => b.text).join("\n\n")}\n`], { type: "text/markdown;charset=utf-8" }), `${stem}.md`);
  } else if (kind === "word") {
    const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}/doc/export`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path }) });
    if (!response.ok) throw new Error(((await response.json().catch(() => null)) as { error?: string } | null)?.error ?? `HTTP ${response.status}`);
    saveBlob(new Blob([await response.arrayBuffer()], { type: DOCX_TYPE }), `${stem}.docx`);
  } else if (canPrintToPdf()) await savePdf(stem);
  else await printPage(stem);
}

/** The page copied into a hidden frame, which is handed to the print dialog ("Save as PDF" there makes
 * the file): a frame of its own keeps the app around the page out of the print, and the comments' marks. */
async function printPage(title: string): Promise<void> {
  const page = document.querySelector<HTMLElement>(".doc-page");
  if (!page) throw new Error("Open the document to print it");
  const frame = document.createElement("iframe");
  frame.setAttribute("aria-hidden", "true");
  frame.style.cssText = "position:fixed;left:-10000px;top:0;width:900px;height:1200px;border:0";
  document.body.appendChild(frame);
  try {
    const target = frame.contentDocument;
    if (!target || !frame.contentWindow) throw new Error("The document could not be prepared for printing");
    target.title = title;
    const styles = [...document.querySelectorAll('link[rel="stylesheet"], style')].map((node) => node.outerHTML).join("");
    target.head.innerHTML = `${styles}<style>@page{margin:18mm}body{margin:0;background:#fff}.doc-page{max-width:none!important;padding:0!important;margin:0!important}.doc-comment-row{display:none}</style>`;
    const copy = page.cloneNode(true) as HTMLElement;
    copy.querySelectorAll(".doc-comment-row").forEach((node) => node.remove());
    copy.querySelectorAll(".doc-commented, .doc-has-comments").forEach((node) => node.classList.remove("doc-commented", "doc-has-comments"));
    target.body.append(copy);
    await Promise.all([target.fonts.ready, ...[...target.images].map((image) => image.decode().catch(() => undefined))]);
    await new Promise<void>((done) => {
      frame.contentWindow?.addEventListener("afterprint", () => done(), { once: true });
      frame.contentWindow?.print();
      setTimeout(done, 120_000);
    });
  } finally {
    frame.remove();
  }
}

/** What the PDF is made of: the page without the comments' marks, and without a chart's source under
 * its drawing. */
function printableCopy(page: HTMLElement): HTMLElement {
  const copy = page.cloneNode(true) as HTMLElement;
  copy.querySelectorAll(".doc-comment-row, pre[data-raw='chart']").forEach((node) => node.remove());
  copy.querySelectorAll(".doc-commented, .doc-has-comments").forEach((node) => node.classList.remove("doc-commented", "doc-has-comments"));
  copy.querySelectorAll("[contenteditable]").forEach((node) => node.removeAttribute("contenteditable"));
  return copy;
}

/** The desktop app prints the window itself, so the window is made to hold only the page for a moment
 * (`body.doc-printing`, in index.css) and in the light theme: a dark page would print dark. */
async function savePdf(title: string): Promise<void> {
  const page = document.querySelector<HTMLElement>(".doc-page");
  if (!page) throw new Error("Open the document to save it as a PDF");
  const root = document.createElement("div");
  root.id = "doc-print-root";
  root.append(printableCopy(page));
  const html = document.documentElement;
  const theme = html.dataset.theme;
  document.body.append(root);
  document.body.classList.add("doc-printing");
  html.dataset.theme = "light";
  try {
    await document.fonts.ready;
    await Promise.all([...root.querySelectorAll("img")].map((image) => image.decode().catch(() => undefined)));
    const bytes = await printToPdf();
    saveBlob(new Blob([bytes as BlobPart], { type: "application/pdf" }), `${title}.pdf`);
  } finally {
    if (theme === undefined) delete html.dataset.theme;
    else html.dataset.theme = theme;
    document.body.classList.remove("doc-printing");
    root.remove();
  }
}
