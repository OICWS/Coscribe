import { lazy, Suspense, useEffect, useState } from "react";
import { type FileKind, type FileRef, looksBinary, MAX_TEXT_BYTES, rawUrl, readsText, splitCsv } from "../../lib/workspaceFiles";

const Markdown = lazy(() => import("../Markdown").then((m) => ({ default: m.Markdown })));
// CodeMirror and its languages load with the first file shown as code, not with the app.
const CodeView = lazy(() => import("./CodeView"));

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
  source,
  wrap,
  refreshKey,
  fallback,
}: {
  threadId: string;
  file: FileRef;
  kind: FileKind;
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
    let cancelled = false;
    void loadText(url)
      .catch(() => ({ error: "Couldn't read this file." }))
      .then((result) => !cancelled && setLoaded(result));
    return () => {
      cancelled = true;
    };
  }, [url, needsText, refreshKey]);

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
  if (kind === "pdf") return <iframe title={file.path} src={fresh} className="h-full w-full border-0" />;
  if (!readsText(kind)) return <div className={note}>{fallback}</div>;
  if (!loaded) return loading;
  if ("error" in loaded) return <div className={note}>{loaded.error}</div>;
  if ("tooBig" in loaded) return <div className={note}>{fallback}<br />This file is too large to show here.</div>;
  if ("binary" in loaded) return <div className={note}>{fallback}</div>;
  if (!source && kind === "markdown") {
    return (
      <div className="h-full overflow-auto px-8 py-6">
        <Suspense fallback={<p className="whitespace-pre-wrap text-sm">{loaded.text}</p>}>
          <div className="plan-doc">
            <Markdown text={loaded.text} />
          </div>
        </Suspense>
      </div>
    );
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
