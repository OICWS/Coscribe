import { lazy, Suspense } from "react";
import { DraftPages, draftPages, type DraftPage } from "../lib/draftPages";
import type { CommentLink } from "../lib/slideComments";
import { isPptx } from "../lib/slides";
import { isDesignCanvas } from "../lib/designCanvas";
import { isDesign, isDocMarkdown, isXlsx } from "../lib/viewers";
import { baseName } from "../lib/fileMentions";
import { openThreadFile, threadFileDownloadUrl } from "../lib/rest";
import { DesignPanel } from "./DesignPanel";
import { SlidesPanel } from "./slides";

// The editor and the canvas load when a document or a canvas is first opened, not with the app.
const DesignCanvasPanel = lazy(() => import("./design").then((m) => ({ default: m.DesignCanvasPanel })));
const SpreadsheetPreview = lazy(() => import("./SpreadsheetPreview"));
const DocPanel = lazy(() => import("./doc").then((m) => ({ default: m.DocPanel })));

const NO_DRAFTS: DraftPage[] = [];

/** The viewer panel's content: a deck in the Slides panel, a Doc in the Doc editor. */
export function ViewerPanel({
  threadId,
  path,
  refreshKey,
  onSendComment,
  onFileChanged,
  busy = false,
  items = [],
}: {
  threadId: string;
  path: string;
  refreshKey: string;
  onSendComment?: (text: string, link?: CommentLink) => void;
  /** The file was renamed (its new path) or deleted (null) from the menu under its name. */
  onFileChanged?: (path: string | null) => void;
  /** coscribe is in the middle of a turn, so the file may be half written. */
  busy?: boolean;
  /** The conversation's log: the slide pages written so far show until the deck is built from them. */
  items?: Parameters<typeof draftPages>[0];
}) {
  if (isXlsx(path)) {
    return <div className="flex h-full min-h-0 min-w-0 flex-col">
      <div className="flex min-w-0 items-center gap-3 border-b border-[var(--border)] px-3 py-2 text-sm">
        <span className="min-w-0 flex-1 truncate" title={path}>{baseName(path)}</span>
        <a className="shrink-0 text-[var(--muted)] hover:underline" href={threadFileDownloadUrl(threadId, path)}
          onClick={(event) => {
            event.preventDefault();
            const download = () => { window.location.href = threadFileDownloadUrl(threadId, path); };
            void openThreadFile(threadId, path, false).then((error) => { if (error) download(); }, download);
          }}>Open in Excel</a>
      </div>
      <div className="min-h-0 flex-1">
        <Suspense fallback={null}>
          <SpreadsheetPreview key={path} path={path} threadId={threadId} refreshKey={refreshKey} />
        </Suspense>
      </div>
    </div>;
  }
  if (isPptx(path)) {
    return (
      <DraftPages.Provider value={busy ? draftPages(items, path) : NO_DRAFTS}>
        <SlidesPanel threadId={threadId} path={path} refreshKey={refreshKey} onSendComment={onSendComment} onFileChanged={onFileChanged} />
      </DraftPages.Provider>
    );
  }
  if (isDocMarkdown(path)) {
    return (
      <Suspense fallback={null}>
        <DocPanel threadId={threadId} path={path} refreshKey={refreshKey} onFileChanged={onFileChanged} onAsk={onSendComment} />
      </Suspense>
    );
  }
  if (isDesignCanvas(path)) {
    return (
      <Suspense fallback={null}>
        <DesignCanvasPanel threadId={threadId} path={path} refreshKey={refreshKey} onFileChanged={onFileChanged} />
      </Suspense>
    );
  }
  if (isDesign(path)) {
    return <DesignPanel threadId={threadId} path={path} refreshKey={refreshKey} onFileChanged={onFileChanged} onSend={onSendComment} busy={busy} />;
  }
  return null;
}
