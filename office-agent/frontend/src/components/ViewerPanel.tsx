import { lazy, Suspense } from "react";
import type { CommentLink } from "../lib/slideComments";
import { isPptx } from "../lib/slides";
import { isDesign, isDocMarkdown } from "../lib/viewers";
import { DesignPanel } from "./DesignPanel";
import { SlidesPanel } from "./slides/SlidesPanel";

// The editor and its library load when a document is first edited, not with the app.
const DocPanel = lazy(() => import("./doc/DocPanel").then((m) => ({ default: m.DocPanel })));

/** The viewer panel's content: a deck in the Slides panel, a Doc in the Doc editor. */
export function ViewerPanel({
  threadId,
  path,
  refreshKey,
  onSendComment,
  onFileChanged,
  busy = false,
}: {
  threadId: string;
  path: string;
  refreshKey: string;
  onSendComment?: (text: string, link?: CommentLink) => void;
  /** The file was renamed (its new path) or deleted (null) from the menu under its name. */
  onFileChanged?: (path: string | null) => void;
  /** coscribe is in the middle of a turn, so the file may be half written. */
  busy?: boolean;
}) {
  if (isPptx(path)) {
    return <SlidesPanel threadId={threadId} path={path} refreshKey={refreshKey} onSendComment={onSendComment} onFileChanged={onFileChanged} busy={busy} />;
  }
  if (isDocMarkdown(path)) {
    return (
      <Suspense fallback={null}>
        <DocPanel threadId={threadId} path={path} refreshKey={refreshKey} onFileChanged={onFileChanged} onAsk={onSendComment} />
      </Suspense>
    );
  }
  if (isDesign(path)) {
    return <DesignPanel threadId={threadId} path={path} refreshKey={refreshKey} onFileChanged={onFileChanged} />;
  }
  return null;
}
