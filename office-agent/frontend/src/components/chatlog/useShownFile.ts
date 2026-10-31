import { useEffect, useState } from "react";
import { isDesignCanvas, readCanvas } from "../../lib/designCanvas";
import { getDoc } from "../../lib/docFile";
import { isDocMarkdown } from "../../lib/viewers";

/** Whether a file a conversation touched is one the app can show: any of its kinds, but a Markdown
 * file only when it is a Doc, which only the server can say. A notes file the model wrote beside a
 * deck gets no card to click that leads nowhere. A design's canvas is written after its pages, so
 * its card waits until the canvas reads, asking again as the turn's calls grow. */
export function useShownFile(threadId: string, path: string, calls = 0): boolean {
  const asDoc = isDocMarkdown(path);
  const asCanvas = isDesignCanvas(path);
  const needsCheck = asDoc || asCanvas;
  const [readable, setReadable] = useState(false);
  useEffect(() => {
    if (!needsCheck) return;
    let live = true;
    // The read the Doc panel opens it with: it answers "not a Doc" for any other Markdown file, and
    // does not wait for the conversation's files to be registered, which happens as a turn ends.
    const read: Promise<unknown> = asCanvas ? readCanvas(threadId, path) : getDoc(threadId, path);
    read.then(
      () => live && setReadable(true),
      () => live && setReadable(false),
    );
    return () => {
      live = false;
    };
  }, [threadId, path, needsCheck, asCanvas, calls]);
  return needsCheck ? readable : true;
}
