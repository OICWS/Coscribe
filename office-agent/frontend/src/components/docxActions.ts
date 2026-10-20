import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { editDocxReview, type DocxOperation, type DocxReview } from "../lib/docxReview";

/** Applies review operations to the file; `reloads` changes once the file was rewritten, and
 * `keepScroll` holds where the page was so the reload can put it back. */
export function useDocxActions(
  threadId: string,
  path: string,
  scroller: RefObject<HTMLDivElement | null>,
  setError: (message: string | null) => void,
) {
  const [busy, setBusy] = useState(false);
  const [reloads, setReloads] = useState(0);
  const keepScroll = useRef<number | null>(null);
  const act = useCallback(
    (operations: DocxOperation[]) => {
      setBusy(true);
      setError(null);
      keepScroll.current = scroller.current?.scrollTop ?? null;
      editDocxReview(threadId, path, operations)
        .then(() => setReloads((n) => n + 1))
        .catch((e: unknown) => {
          keepScroll.current = null;
          setError(e instanceof Error ? e.message : String(e));
        })
        .finally(() => setBusy(false));
    },
    [threadId, path, scroller, setError],
  );
  return { busy, reloads, keepScroll, act };
}

/** The tracked change picked on the page. The page's marks and the review's changes are both in
 * document order, so the n-th mark is the n-th change while `matched` says the counts agree. */
export function useChangeSelection(page: RefObject<HTMLDivElement | null>, review: DocxReview | null, matched: boolean) {
  const [selected, setSelected] = useState<string | null>(null);
  const marks = useCallback(() => [...(page.current?.querySelectorAll("ins, del") ?? [])], [page]);
  useEffect(() => {
    const els = marks();
    els.forEach((el) => el.classList.remove("docx-selected"));
    const at = review?.changes.findIndex((c) => c.id === selected) ?? -1;
    if (matched && at >= 0) els[at]?.classList.add("docx-selected");
  }, [selected, review, matched, marks]);
  const pick = (target: Element | null | undefined) => {
    const el = target?.closest("ins, del");
    const at = el && matched ? marks().indexOf(el) : -1;
    setSelected(at >= 0 ? (review?.changes[at]?.id ?? null) : null);
  };
  return {
    pick,
    selectedChange: review?.changes.find((c) => c.id === selected) ?? null,
  };
}
