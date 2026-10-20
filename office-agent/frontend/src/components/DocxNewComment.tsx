import { useEffect, useState, type RefObject } from "react";
import { askMessage, commentOn, type DocxOperation } from "../lib/docxReview";

/** The words selected on the page, kept after the selection is lost to a click in the comment box. */
function useSelectedWords(page: RefObject<HTMLDivElement | null>) {
  const [words, setWords] = useState("");
  const [pageNo, setPageNo] = useState(1);
  useEffect(() => {
    const onChange = () => {
      const selection = document.getSelection();
      const text = selection?.toString().trim() ?? "";
      if (text && selection?.anchorNode && page.current?.contains(selection.anchorNode)) {
        setWords(text);
        const section = (selection.anchorNode instanceof Element ? selection.anchorNode : selection.anchorNode.parentElement)?.closest("section.docx");
        setPageNo(Math.max(0, Array.from(page.current.querySelectorAll("section.docx")).indexOf(section as Element)) + 1);
      }
    };
    document.addEventListener("selectionchange", onChange);
    return () => document.removeEventListener("selectionchange", onChange);
  }, [page]);
  return [words, setWords, pageNo] as const;
}

/** A bar for a new comment on the words selected on the page. */
export function DocxNewComment({
  page,
  file,
  busy,
  onAct,
  onAsk,
}: {
  page: RefObject<HTMLDivElement | null>;
  file: string;
  busy: boolean;
  onAct: (operations: DocxOperation[]) => void;
  onAsk?: (text: string) => void;
}) {
  const [words, setWords, pageNo] = useSelectedWords(page);
  const [text, setText] = useState("");
  if (!words) return null;
  const send = () => {
    onAct(commentOn(words, text));
    setText("");
    setWords("");
  };
  return (
    <div className="flex h-9 shrink-0 items-center gap-2 border-b border-[var(--border)] px-3 text-xs">
      <span className="max-w-[30%] shrink-0 truncate text-[var(--muted)]" title={words}>
        “{words}”
      </span>
      <input
        aria-label="New comment"
        value={text}
        placeholder="Comment on the selected words"
        className="min-w-0 flex-1 rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 py-0.5"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && text.trim()) send();
        }}
      />
      <button
        type="button"
        className="shrink-0 rounded-md border border-[var(--border)] px-2 py-0.5 hover:bg-[var(--card-bg)] disabled:opacity-40"
        disabled={busy || !text.trim()}
        onClick={send}
      >
        Comment
      </button>
      {onAsk && (
        <button
          type="button"
          className="shrink-0 rounded-md border border-[var(--border)] px-2 py-0.5 hover:bg-[var(--card-bg)]"
          onClick={() => {
            onAsk(askMessage(file, pageNo, words));
            setWords("");
          }}
        >
          Ask coscribe
        </button>
      )}
      <button
        type="button"
        className="shrink-0 rounded-md border border-[var(--border)] px-2 py-0.5 hover:bg-[var(--card-bg)]"
        onClick={() => setWords("")}
      >
        Cancel
      </button>
    </div>
  );
}
