import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { GlobalWorkerOptions, TextLayer, type PDFDocumentProxy, type PDFPageProxy } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import "pdfjs-dist/web/pdf_viewer.css";
import { openThreadFile } from "../lib/rest";
import { useWordPreview } from "./useWordPreview";

GlobalWorkerOptions.workerSrc = workerUrl;

const pointsToPixels = 96 / 72;
const control = "h-7 rounded-md bg-transparent px-2 text-sm hover:bg-[var(--card-bg)] disabled:opacity-40";

function WordPage({ pdf, number, zoom, fitWidth }: { pdf: PDFDocumentProxy; number: number; zoom: string; fitWidth: number }) {
  const surface = useRef<HTMLDivElement>(null);
  const [nearby, setNearby] = useState(false);
  const [loaded, setPage] = useState<{ pdf: PDFDocumentProxy; page: PDFPageProxy }>();
  const page = loaded?.pdf === pdf ? loaded.page : null;
  const [failed, setFailed] = useState(false);
  const scale = zoom === "fit"
    ? Math.min(fitWidth / (page?.getViewport({ scale: 1 }).width ?? 595), 2.5)
    : Number(zoom) * pointsToPixels / 100;

  useEffect(() => {
    const element = surface.current;
    if (!element) return;
    const observer = new IntersectionObserver(([entry]) => setNearby(entry.isIntersecting), { rootMargin: "300px" });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!nearby || page) return;
    let cancelled = false;
    void pdf.getPage(number)
      .then((next) => { if (!cancelled) setPage({ pdf, page: next }); })
      .catch(() => { if (!cancelled) setFailed(true); });
    return () => { cancelled = true; };
  }, [pdf, number, nearby, page]);

  useEffect(() => {
    const element = surface.current;
    if (!page || !nearby || !element) return;
    const viewport = page.getViewport({ scale });
    const canvas = document.createElement("canvas");
    const density = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.ceil(viewport.width * density);
    canvas.height = Math.ceil(viewport.height * density);
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.setAttribute("aria-hidden", "true");
    const text = document.createElement("div");
    text.className = "textLayer";
    element.replaceChildren(canvas, text);
    const drawing = page.render({ canvas, viewport, transform: [density, 0, 0, density, 0, 0] });
    const layer = new TextLayer({ textContentSource: page.streamTextContent(), container: text, viewport });
    let cancelled = false;
    void Promise.all([drawing.promise, layer.render()]).catch(() => {
      if (!cancelled) setFailed(true);
    });
    return () => {
      cancelled = true;
      drawing.cancel();
      layer.cancel();
      canvas.remove();
      text.remove();
    };
  }, [page, scale, nearby]);

  const viewport = page?.getViewport({ scale });
  return (
    <section aria-label={`Page ${number}`} data-word-page={number} className="relative shrink-0 bg-white shadow-sm ring-1 ring-black/10">
      <div
        ref={surface}
        className="relative"
        style={{
          width: viewport?.width ?? 595 * scale,
          height: viewport?.height ?? 842 * scale,
          "--total-scale-factor": scale * (viewport?.userUnit ?? 1),
        } as CSSProperties}
      />
      {failed && <p role="alert" className="absolute inset-x-0 top-0 bg-white p-4 text-black">This page could not be rendered.</p>}
    </section>
  );
}

export default function WordPreview({ threadId, path }: { threadId: string; path: string }) {
  const [zoom, setZoom] = useState("fit");
  const [active, setActive] = useState(1);
  const [width, setWidth] = useState(640);
  const [openError, setOpenError] = useState<string | null>(null);
  const scroll = useRef<HTMLDivElement>(null);
  const restore = useRef<{ page: number; offset: number }>(null);
  const query = new URLSearchParams({ path, thread_id: threadId });
  const keepPosition = () => {
    const root = scroll.current;
    const page = root?.querySelector<HTMLElement>(`[data-word-page="${active}"]`);
    if (root && page) restore.current = { page: active, offset: root.getBoundingClientRect().top - page.getBoundingClientRect().top };
  };
  const { pdf, error, retry } = useWordPreview(query, keepPosition);
  const pages = pdf?.numPages ?? 0;
  const fitWidth = Math.max(width - 48, 100);

  useEffect(() => {
    const element = scroll.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useLayoutEffect(() => {
    const root = scroll.current;
    const saved = restore.current;
    if (!pdf || !root || !saved) return;
    const number = Math.min(saved.page, pdf.numPages);
    const page = root.querySelector<HTMLElement>(`[data-word-page="${number}"]`);
    if (page) root.scrollTop += page.getBoundingClientRect().top - root.getBoundingClientRect().top + saved.offset;
    restore.current = null;
    setActive(number);
  }, [pdf]);

  const pageAtTop = () => {
    const root = scroll.current;
    if (!root) return;
    const page = root.scrollTop > 0 && root.scrollHeight - root.scrollTop <= root.clientHeight + 2
      ? root.querySelector<HTMLElement>(`[data-word-page="${pages}"]`)
      : Array.from(root.querySelectorAll<HTMLElement>("[data-word-page]"))
        .find((element) => element.getBoundingClientRect().bottom > root.getBoundingClientRect().top + 32);
    if (page) setActive(Number(page.dataset.wordPage));
  };
  const current = Math.min(active, pages);
  const openOriginal = () => void openThreadFile(threadId, path, false)
    .then(setOpenError).catch(() => setOpenError("Couldn't open the original Word file."));
  return (
    <div className="relative flex h-full min-h-0 flex-col">
      {openError && <p role="alert" className="px-4 py-2 text-sm text-[var(--danger)]">{openError}</p>}
      <div ref={scroll} onScroll={pageAtTop} className="min-h-0 flex-1 overflow-auto bg-[var(--card-bg)]">
        {!pdf && !error && <p role="status" className="p-6 text-center text-sm text-[var(--muted)]">Preparing Word preview…</p>}
        {error && <div role="alert" className="flex items-center justify-center gap-3 p-4 text-sm text-[var(--muted)]">
          <span>{error}</span><button type="button" className={`${control} border border-[var(--border)]`} onClick={retry}>Retry</button>
        </div>}
        {pdf && (
          <div className="flex w-max min-w-full flex-col items-center gap-5 p-6" key={pdf.fingerprints.join(":")}>
            {Array.from({ length: pages }, (_, i) => <WordPage key={i} pdf={pdf} number={i + 1} zoom={zoom} fitWidth={fitWidth} />)}
          </div>
        )}
      </div>
      {/* Pages turn by scrolling; the controls float over the corner instead of taking a row. */}
      <div className="absolute bottom-4 right-6 flex items-center gap-1 rounded-lg border border-[var(--border)] bg-[var(--bg)] p-1 text-sm shadow-[0_2px_10px_rgba(0,0,0,0.08)]">
        {pages > 0 && <span aria-live="polite" className="px-2 tabular-nums text-[var(--muted)]">
          <span aria-hidden="true">{current} / {pages}</span><span className="sr-only">Page {current} of {pages}</span>
        </span>}
        <select aria-label="Zoom" className={control} value={zoom} onChange={(event) => setZoom(event.target.value)}>
          <option value="fit">Fit width</option>
          {[75, 100, 125, 150, 200].map((level) => <option key={level} value={level}>{level}%</option>)}
        </select>
        <button type="button" className={control} onClick={openOriginal}>Open in Word</button>
      </div>
    </div>
  );
}
