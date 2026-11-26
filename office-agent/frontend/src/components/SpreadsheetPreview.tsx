import { useEffect, useState } from "react";
import { SpreadsheetGrid } from "./SpreadsheetGrid";
import type { WorkbookPreview } from "./spreadsheetModel";
import "./spreadsheetPreview.css";

export default function SpreadsheetPreview({ threadId, path, refreshKey = "" }: {
  threadId: string;
  path: string;
  refreshKey?: string;
}) {
  const [requested, setRequested] = useState<string | null>(null);
  const [loaded, setLoaded] = useState<WorkbookPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    const params = new URLSearchParams({ thread_id: threadId, path });
    if (requested !== null) params.set("sheet", requested);
    async function load() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`/api/attachment/xlsx?${params}`, { method: "POST", signal: abort.signal });
        const data: WorkbookPreview = await response.json();
        if (!response.ok) throw new Error(data.error || "This workbook could not be opened.");
        if (!abort.signal.aborted) {
          setLoaded(data);
          if (!data.sheet && requested !== null) setRequested(null);
        }
      } catch (failure) {
        if (!abort.signal.aborted) setError(failure instanceof Error && failure.message.startsWith("This workbook")
          ? failure.message : "This workbook could not be opened.");
      } finally {
        if (!abort.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => abort.abort();
  }, [path, threadId, refreshKey, requested]);

  return <section className="spreadsheet-preview" aria-label="Excel preview" aria-busy={loading}>
    {loading && !loaded && <div className="spreadsheet-status" role="status">Loading workbook…</div>}
    {error && <div className="spreadsheet-status" role="status">{error}</div>}
    {!loading && !error && !loaded?.sheet && <div className="spreadsheet-status">No visible worksheets.</div>}
    {loaded?.sheet && !error && <SpreadsheetGrid key={loaded.sheet.name} sheet={loaded.sheet} />}
    {!!loaded?.sheets.length && (
      <div className="spreadsheet-footer">
        <div className="spreadsheet-tabs" aria-label="Worksheets">
          {loaded.sheets.map((name) => <button
            type="button" key={name} aria-pressed={loaded.sheet?.name === name}
            onClick={() => { if (loaded.sheet?.name !== name || error) setRequested(name); }}
          >{name}</button>)}
        </div>
        <span className="spreadsheet-note" role="status">{loading ? "Loading…" : "Read-only"}</span>
      </div>
    )}
  </section>;
}
