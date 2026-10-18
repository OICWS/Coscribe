import { useEffect, useState } from "react";
import { getSlideHistory, stepSlideHistory, type SlideHistory } from "../../lib/slideEditing";

const NONE: SlideHistory = { undo: null, redo: null };

/** Undo and redo for the deck: what each would do, read again whenever the deck changes
 * (`version`), and the step itself, after which the deck is read again (`onStepped`). */
export function useSlideHistory(
  threadId: string,
  path: string,
  version: string,
  onStepped: () => void,
  onProblem: (message: string | null) => void,
) {
  const [history, setHistory] = useState<SlideHistory>(NONE);
  useEffect(() => {
    let live = true;
    getSlideHistory(threadId, path).then(
      (read) => live && setHistory(read),
      () => live && setHistory(NONE),
    );
    return () => {
      live = false;
    };
  }, [threadId, path, version]);
  const step = (action: "undo" | "redo") => {
    if (!history[action]) return;
    stepSlideHistory(threadId, path, action).then(
      (read) => {
        setHistory(read);
        onProblem(null);
        onStepped();
      },
      (e: unknown) => onProblem(e instanceof Error ? e.message : String(e)),
    );
  };
  return { history, step };
}
