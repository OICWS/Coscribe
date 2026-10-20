import type { CommentLink } from "../lib/slideComments";
import { isPptx } from "../lib/slides";
import { DocxViewerPanel } from "./DocxViewerPanel";
import { SlidesPanel } from "./slides/SlidesPanel";

/** The viewer panel's content: a deck in the Slides panel, a Word file in the Word viewer. */
export function ViewerPanel({
  threadId,
  path,
  refreshKey,
  onSendComment,
}: {
  threadId: string;
  path: string;
  refreshKey: string;
  onSendComment?: (text: string, link?: CommentLink) => void;
}) {
  return isPptx(path) ? (
    <SlidesPanel threadId={threadId} path={path} refreshKey={refreshKey} onSendComment={onSendComment} />
  ) : (
    <DocxViewerPanel threadId={threadId} path={path} refreshKey={refreshKey} onAsk={onSendComment} />
  );
}
