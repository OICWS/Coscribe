import { useEffect, useState } from "react";
import { getDoc } from "../../lib/docFile";
import { isDocMarkdown } from "../../lib/viewers";

/** Whether a file a conversation touched is one the app can show: any of its kinds, but a Markdown
 * file only when it is a Doc, which only the server can say. A notes file the model wrote beside a
 * deck gets no card to click that leads nowhere. */
export function useShownFile(threadId: string, path: string): boolean {
  const needsCheck = isDocMarkdown(path);
  const [isDoc, setIsDoc] = useState(false);
  useEffect(() => {
    if (!needsCheck) return;
    let live = true;
    // The read the Doc panel opens it with: it answers "not a Doc" for any other Markdown file, and
    // does not wait for the conversation's files to be registered, which happens as a turn ends.
    getDoc(threadId, path).then(
      () => live && setIsDoc(true),
      () => live && setIsDoc(false),
    );
    return () => {
      live = false;
    };
  }, [threadId, path, needsCheck]);
  return needsCheck ? isDoc : true;
}
