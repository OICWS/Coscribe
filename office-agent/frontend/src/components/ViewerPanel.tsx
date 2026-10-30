import { lazy, Suspense } from "react";
import { DraftPages, draftPages, type DraftPage } from "../lib/draftPages";
import type { CommentLink } from "../lib/slideComments";
import { isPptx } from "../lib/slides";
import { isDesignCanvas } from "../lib/designCanvas";
import { isDesign, isDocMarkdown } from "../lib/viewers";
import { DesignPanel } from "./DesignPanel";
import { SlidesPanel } from "./slides/SlidesPanel";

// The editor and the canvas load when a document or a canvas is first opened, not with the app.
const DesignCanvasPanel = lazy(() => import("./design/DesignCanvasPanel").then((m) => ({ default: m.DesignCanvasPanel })));
const DocPanel = lazy(() => import("./doc/DocPanel").then((m) => ({ default: m.DocPanel })));

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
  if (isPptx(path)) {
    return (
      <DraftPages.Provider value={busy ? draftPages(items) : NO_DRAFTS}>
        <SlidesPanel threadId={threadId} path={path} refreshKey={refreshKey} onSendComment={onSendComment} onFileChanged={onFileChanged} busy={busy} />
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
