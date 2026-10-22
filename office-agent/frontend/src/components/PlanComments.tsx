import { useState } from "react";
import type { PlanComment } from "../lib/planComments";
import { CloseIcon, PlusIcon } from "./icons";

/** The box that opens under selected words: type, then Enter or the plus. */
export function CommentBox({ top, onAdd, onCancel }: { top: number; onAdd: (text: string) => void; onCancel: () => void }) {
  const [text, setText] = useState("");
  const submit = () => {
    if (text.trim()) onAdd(text.trim());
  };
  return (
    <div
      className="absolute left-5 right-5 z-10 flex items-center gap-2 rounded-2xl border border-[var(--border)] bg-[var(--bg)] py-2 pl-4 pr-2.5 shadow-[0_4px_16px_rgba(0,0,0,0.08)]"
      style={{ top }}
    >
      <input
        autoFocus
        aria-label="Add a comment"
        placeholder="Add a comment"
        className="min-w-0 flex-1 bg-transparent py-1.5 text-[15px] outline-none placeholder:text-[var(--muted)]"
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.nativeEvent.isComposing) submit();
          else if (event.key === "Escape") onCancel();
        }}
      />
      <button
        type="button"
        title="Add comment"
        disabled={!text.trim()}
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[var(--border)] text-[var(--muted)] enabled:hover:text-[var(--fg)] disabled:opacity-50"
        onClick={submit}
      >
        <PlusIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

/** The comments waiting to be sent with Revise. */
export function CommentList({ comments, onRemove }: { comments: PlanComment[]; onRemove: (id: string) => void }) {
  return (
    <section className="mt-6">
      <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Comments</h2>
      <ul className="flex flex-col gap-3">
        {comments.map((comment) => (
          <li key={comment.id} className="flex items-start gap-2 text-[15px] leading-6">
            <div className="min-w-0 flex-1">
              <p className="truncate border-l-2 border-[var(--border)] pl-2.5 text-[13px] text-[var(--muted)]">{comment.quote}</p>
              <p className="mt-1 [overflow-wrap:anywhere]">{comment.text}</p>
            </div>
            <button
              type="button"
              title="Remove comment"
              className="mt-0.5 shrink-0 rounded-md p-1 text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
              onClick={() => onRemove(comment.id)}
            >
              <CloseIcon className="h-3.5 w-3.5" />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
