import { lazy, Suspense, useEffect, useState } from "react";
import { type FileKind, type FileRef, looksBinary, MAX_TEXT_BYTES, rawUrl, readsText, splitCsv } from "../../lib/workspaceFiles";

type MarkdownModule = typeof import("../Markdown");
// Held once loaded so a later file renders it directly: React.lazy suspends on every new mount,
// and React holds a revealed fallback for about 300 ms, which showed as a flash before the page.
let markdownModule: MarkdownModule | undefined;
const loadMarkdown = () => import("../Markdown").then((m) => (markdownModule = m));
const Markdown = lazy(() => loadMarkdown().then((m) => ({ default: m.Markdown })));
// CodeMirror and its languages load with the first file shown as code, not with the app.
const SpreadsheetPreview = lazy(() => import("../SpreadsheetPreview"));
const CodeView = lazy(() => import("./CodeView"));
const PresentationPreview = lazy(() => import("./PresentationPreview"));
const DocFileReading = lazy(() => import("../doc").then((m) => ({ default: m.DocFileReading })));
const WordPreview = lazy(() => import("../WordPreview"));

type Loaded = { text: string } | { error: string } | { tooBig: true } | { binary: true } | null;

async function loadText(url: string): Promise<Loaded> {
  const res = await fetch(url);
  if (!res.ok) return { error: res.status === 404 ? "This file is no longer there." : "Couldn't read this file." };
  if (Number(res.headers.get("content-length") ?? 0) > MAX_TEXT_BYTES) {
    void res.body?.cancel();
    return { tooBig: true };
  }
  const text = await res.text();
  return looksBinary(text) ? { binary: true } : { text };
}

const note = "flex h-full items-center justify-center px-6 text-center text-sm text-[var(--muted)]";
const loading = <p className="px-5 py-4 text-sm text-[var(--muted)]">Loading...</p>;

/** One file as the panel shows it: drawn (`preview`) or as highlighted source. */
export function FilePreview({
  threadId,
  file,
  kind,
  path,
  source,
  wrap,
  refreshKey,
  fallback,
}: {
  threadId: string;
  file: FileRef;
  kind: FileKind;
  path?: string;
  source: boolean;
  /** Long lines of source wrap instead of scrolling sideways. */
  wrap: boolean;
  refreshKey: string;
  /** What to offer for a file that has no preview here. */
  fallback: React.ReactNode;
}) {
  const url = rawUrl(threadId, file);
  const [loaded, setLoaded] = useState<Loaded>(null);
  const needsText = readsText(kind) && (source || kind !== "html" && kind !== "svg");

  useEffect(() => {
    if (!needsText) return;
    // The renderer's chunk loads beside the text, so the page appears once, already rendered.
    const renderer = kind === "markdown" && !source && !markdownModule ? loadMarkdown().catch(() => undefined) : undefined;
    let cancelled = false;
    void Promise.all([loadText(url), renderer]).then(([text]) => text)
      .catch(() => ({ error: "Couldn't read this file." }))
      .then((result) => !cancelled && setLoaded(result));
    return () => {
      cancelled = true;
    };
  }, [url, needsText, refreshKey, kind, source]);

  // The key makes a changed file load again instead of keeping the browser's copy of the page.
  const fresh = `${url}${url.includes("?") ? "&" : "?"}v=${encodeURIComponent(refreshKey)}`;
  if (!source && (kind === "image" || kind === "svg")) {
    return (
      <div className="files-checker flex h-full items-center justify-center overflow-auto p-6">
        <img src={fresh} alt={file.path} className="max-h-full max-w-full object-contain" />
      </div>
    );
  }
  if (!source && kind === "html") {
    return <iframe title={file.path} src={fresh} sandbox="allow-same-origin" className="h-full w-full border-0 bg-white" />;
  }
  if (kind === "pptx" && path) return <Suspense fallback={loading}>
    <PresentationPreview threadId={threadId} path={path} revision={refreshKey} />
  </Suspense>;
  if (kind === "xlsx" && path) return <Suspense fallback={loading}>
    <SpreadsheetPreview threadId={threadId} path={path} refreshKey={refreshKey} />
  </Suspense>;
  if (kind === "pdf") return <iframe title={file.path} src={fresh} className="h-full w-full border-0" />;
  if (kind === "docx" && path) return <Suspense fallback={loading}><WordPreview key={path} threadId={threadId} path={path} /></Suspense>;
  if (!readsText(kind)) return <div className={note}>{fallback}</div>;
  if (!loaded) return loading;
  if ("error" in loaded) return <div className={note}>{loaded.error}</div>;
  if ("tooBig" in loaded) return <div className={note}>{fallback}<br />This file is too large to show here.</div>;
  if ("binary" in loaded) return <div className={note}>{fallback}</div>;
  if (!source && kind === "markdown") {
    const markdown = <div className="h-full overflow-auto px-8 py-6">
      {markdownModule ? <div className="plan-doc"><markdownModule.Markdown text={loaded.text} /></div> : <Suspense fallback={null}>
        <div className="plan-doc"><Markdown text={loaded.text} /></div>
      </Suspense>}
    </div>;
    return path && /^\uFEFF?[ \t]*---[ \t]*\r?\n/.test(loaded.text)
      ? <Suspense fallback={loading}><DocFileReading threadId={threadId} path={path} revision={refreshKey} markdown={markdown} /></Suspense>
      : markdown;
  }
  if (!source && kind === "csv") return <CsvTable text={loaded.text} tabs={/\.tsv$/i.test(file.path)} />;
  return (
    <Suspense fallback={loading}>
      <CodeView text={loaded.text} name={file.path} wrap={wrap} />
    </Suspense>
  );
}

function CsvTable({ text, tabs }: { text: string; tabs: boolean }) {
  const [head, ...rows] = splitCsv(text, tabs ? "\t" : ",");
  if (!head) return <div className={note}>This file is empty.</div>;
  const cell = "max-w-[320px] truncate border-b border-r border-[var(--border)] px-3 py-1.5";
  return (
    <div className="h-full overflow-auto">
      <table className="border-separate border-spacing-0 text-[13px]">
        <thead className="sticky top-0 bg-[var(--card-bg)]">
          <tr>{head.map((name, i) => <th key={i} className={`${cell} text-left font-medium`}>{name}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r}>{head.map((_, i) => <td key={i} title={row[i]} className={cell}>{row[i] ?? ""}</td>)}</tr>
          ))}
        </tbody>
      </table>
      {rows.length >= 999 && <p className="px-3 py-2 text-xs text-[var(--muted)]">Showing the first 1,000 rows.</p>}
    </div>
  );
}
