import { useEffect, useRef, useState, type CSSProperties } from "react";
import { getDocument, GlobalWorkerOptions, TextLayer, type PDFDocumentProxy, type PDFPageProxy } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import "pdfjs-dist/web/pdf_viewer.css";
import { openThreadFile } from "../lib/rest";

GlobalWorkerOptions.workerSrc = workerUrl;

type Preview = { pdf: PDFDocumentProxy } | { error: string };
const pointsToPixels = 96 / 72;
const control = "h-8 rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 text-sm hover:bg-[var(--card-bg)] disabled:opacity-40";

function useWordPreview(url: string) {
  const [revision, setRevision] = useState(0);
  const [loaded, setLoaded] = useState<{ url: string; revision: number; preview: Preview } | null>(null);

  useEffect(() => {
    const abort = new AbortController();
    let task: ReturnType<typeof getDocument> | undefined;
    let version: string | null = null;
    let checking = false;
    const finish = (preview: Preview) => {
      if (!abort.signal.aborted) setLoaded({ url, revision, preview });
    };
    const load = async () => {
      const response = await fetch(url, { signal: abort.signal });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.error ?? "Couldn't prepare this Word preview.");
      }
      const data = await response.arrayBuffer();
      if (abort.signal.aborted) return;
      task = getDocument({ data, isEvalSupported: false, useWasm: false });
      const pdf = await task.promise;
      version = response.headers.get("ETag");
      finish({ pdf });
    };
    void load().catch((error: Error) => {
      finish({ error: error.message });
    });
    const timer = window.setInterval(async () => {
      if (checking || version === null || document.hidden) return;
      checking = true;
      try {
        const response = await fetch(url, { method: "HEAD", signal: abort.signal });
        const changed = response.ok && response.headers.get("ETag") !== version;
        if (!abort.signal.aborted && (changed || response.status === 403 || response.status === 404)) {
          setRevision((value) => value + 1);
        }
      } catch {
        // Keep the page visible during a transient check failure.
      } finally {
        checking = false;
      }
    }, 2500);
    return () => {
      abort.abort();
      window.clearInterval(timer);
      void task?.destroy().catch(() => undefined);
    };
  }, [url, revision]);
  return {
    preview: loaded?.url === url && loaded.revision === revision ? loaded.preview : null,
    revision,
    refresh: () => setRevision((value) => value + 1),
  };
}

function WordPage({ pdf, number, zoom, fitWidth }: { pdf: PDFDocumentProxy; number: number; zoom: string; fitWidth: number }) {
  const surface = useRef<HTMLDivElement>(null);
  const [nearby, setNearby] = useState(false);
  const [page, setPage] = useState<PDFPageProxy | null>(null);
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
      .then((next) => { if (!cancelled) setPage(next); })
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
  const url = `/api/attachment/docx?${new URLSearchParams({ path, thread_id: threadId })}`;
  const { preview, revision, refresh } = useWordPreview(url);
  const pages = preview && "pdf" in preview ? preview.pdf.numPages : 0;
  const fitWidth = Math.max(width - 48, 100);

  useEffect(() => {
    const element = scroll.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const goTo = (page: number) => {
    scroll.current?.querySelector(`[data-word-page="${page}"]`)?.scrollIntoView({ block: "start", inline: "nearest" });
  };
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
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] px-3 py-2">
        <div className="flex items-center gap-2">
          <button type="button" aria-label="Previous page" className={control} disabled={current <= 1} onClick={() => goTo(current - 1)}>‹</button>
          <span aria-live="polite" className="whitespace-nowrap text-sm tabular-nums">{pages ? `Page ${current} of ${pages}` : "Word preview"}</span>
          <button type="button" aria-label="Next page" className={control} disabled={current >= pages} onClick={() => goTo(current + 1)}>›</button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select aria-label="Zoom" className={control} value={zoom} onChange={(event) => setZoom(event.target.value)}>
            <option value="fit">Fit width</option>
            {[75, 100, 125, 150, 200].map((level) => <option key={level} value={level}>{level}%</option>)}
          </select>
          <button type="button" className={control} onClick={refresh}>Refresh</button>
          <button type="button" className={control} onClick={openOriginal}>Open in Word</button>
        </div>
      </div>
      {openError && <p role="alert" className="px-4 py-2 text-sm text-[var(--danger)]">{openError}</p>}
      <div ref={scroll} onScroll={pageAtTop} className="min-h-0 flex-1 overflow-auto bg-[var(--card-bg)]">
        {!preview && <p role="status" className="p-6 text-center text-sm text-[var(--muted)]">Preparing Word preview…</p>}
        {preview && "error" in preview && <p role="alert" className="p-6 text-center text-sm text-[var(--muted)]">{preview.error}</p>}
        {preview && "pdf" in preview && (
          <div className="flex w-max min-w-full flex-col items-center gap-5 p-6" key={revision}>
            {Array.from({ length: pages }, (_, i) => <WordPage key={i} pdf={preview.pdf} number={i + 1} zoom={zoom} fitWidth={fitWidth} />)}
          </div>
        )}
      </div>
    </div>
  );
}
