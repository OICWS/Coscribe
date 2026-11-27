import { getDocument, type PDFDocumentProxy } from "pdfjs-dist";
import { useEffect, useRef, useState } from "react";

type View = { url: string; pdf?: PDFDocumentProxy; error?: string };

export function useWordPreview(query: URLSearchParams, beforeReplace: () => void) {
  const address = query.toString();
  const url = `/api/attachment/docx?${address}`;
  const events = `/api/attachment/docx/versions?${address}`;
  const [view, setView] = useState<View>();
  const retry = useRef<() => void>(() => undefined);
  const prepareSwap = useRef(beforeReplace);
  useEffect(() => { prepareSwap.current = beforeReplace; }, [beforeReplace]);

  const visible = view?.url === url ? view : undefined;
  const pdf = visible?.pdf;
  useEffect(() => () => { void pdf?.destroy().catch(() => undefined); }, [pdf]);

  useEffect(() => {
    const abort = new AbortController();
    const changes = new EventSource(events);
    let desired: string | null | undefined;
    let published: string | null | undefined;
    let pending: ReturnType<typeof getDocument> | undefined;
    let running = false;
    let rerun = false;
    let retriedConflict = false;

    async function load() {
      if (abort.signal.aborted) return;
      if (running) { rerun = true; return; }
      running = true;
      const started = desired;
      let received: string | null | undefined;
      try {
        const response = await fetch(url, { method: "POST", signal: abort.signal });
        if (response.status === 409 && !retriedConflict) {
          retriedConflict = true;
          rerun = true;
          return;
        }
        if (!response.ok) {
          const body = await response.json().catch(() => null);
          throw new Error(body?.error ?? "Couldn't prepare this Word preview.");
        }
        received = response.headers.get("ETag");
        const data = await response.arrayBuffer();
        if (abort.signal.aborted || (desired !== started && desired !== received)) return;
        pending = getDocument({ data, useWasm: false });
        const pdf = await pending.promise;
        if (abort.signal.aborted || (desired !== started && desired !== received)) return;
        pending = undefined;
        published = received;
        prepareSwap.current();
        setView({ url, pdf });
      } catch (error) {
        if (!abort.signal.aborted && desired === started) {
          const message = error instanceof Error ? error.message : "Couldn't prepare this Word preview.";
          setView((before) => ({ url, pdf: before?.url === url ? before.pdf : undefined, error: message }));
        }
      } finally {
        void pending?.destroy().catch(() => undefined);
        pending = undefined;
        running = false;
        if (rerun && (received === undefined || desired !== received)) {
          rerun = false;
          void load();
        } else rerun = false;
      }
    }

    changes.onmessage = (event: MessageEvent<string>) => {
      const version = JSON.parse(event.data) as string | null;
      if (version === desired) return;
      desired = version;
      retriedConflict = false;
      if (version !== published) void load();
    };

    retry.current = () => {
      retriedConflict = false;
      setView((before) => before?.url === url ? { ...before, error: undefined } : before);
      void load();
    };
    void load();
    return () => {
      changes.close();
      abort.abort();
      void pending?.destroy().catch(() => undefined);
    };
  }, [url, events]);

  return { pdf, error: visible?.error, retry: () => retry.current() };
}
