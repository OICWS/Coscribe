import { useState } from "react";
import { replyTo, setResolved, type DocxComment, type DocxOperation } from "../lib/docxReview";
import { formatRunTime } from "../lib/runLabels";
import { CheckIcon } from "./icons";

const textButton =
  "shrink-0 rounded-md border border-[var(--border)] px-2 py-0.5 text-xs hover:bg-[var(--card-bg)] disabled:opacity-40";

export function DocxCommentCard({
  comment,
  top,
  active,
  busy,
  onActivate,
  onAct,
  cardRef,
}: {
  comment: DocxComment;
  top?: number;
  active: boolean;
  busy: boolean;
  onActivate: () => void;
  onAct: (operations: DocxOperation[]) => void;
  cardRef?: (el: HTMLElement | null) => void;
}) {
  const [draft, setDraft] = useState("");
  const placed = top !== undefined;
  const base = `${placed ? "absolute inset-x-0" : "mb-2"} rounded-xl border bg-[var(--card-bg)] text-[13px] transition-[top,box-shadow] duration-150 motion-reduce:transition-none`;
  const look = active
    ? "z-10 border-[var(--accent)] shadow-[var(--panel-shadow)]"
    : "border-[var(--border)] hover:border-[var(--border-hover)]";
  if (comment.done && !active) {
    return (
      <button
        ref={cardRef}
        type="button"
        style={placed ? { top } : undefined}
        className={`${base} ${look} flex w-full items-center gap-2 px-3 py-1.5 text-left text-[var(--muted)]`}
        onClick={(e) => {
          e.stopPropagation();
          onActivate();
        }}
      >
        <CheckIcon className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">
          {comment.author}: {comment.text}
        </span>
      </button>
    );
  }
  const send = () => {
    if (!draft.trim()) return;
    onAct(replyTo(comment.id, draft));
    setDraft("");
  };
  return (
    <article
      ref={cardRef}
      style={placed ? { top } : undefined}
      className={`${base} ${look} cursor-default px-3 py-2.5`}
      onClick={(e) => {
        e.stopPropagation();
        onActivate();
      }}
    >
      <Entry author={comment.author} initials={comment.initials} date={comment.date} text={comment.text} />
      {comment.done && <div className="mt-1 text-xs text-[var(--muted)]">Resolved</div>}
      {comment.replies.map((reply) => (
        <div key={reply.id} className="mt-2.5 border-t border-[var(--border)] pt-2.5">
          <Entry author={reply.author} initials={reply.initials} date={reply.date} text={reply.text} />
        </div>
      ))}
      {active && (
        <div className="mt-2.5 border-t border-[var(--border)] pt-2.5">
          <textarea
            aria-label="Reply"
            rows={2}
            value={draft}
            placeholder="Reply"
            className="w-full resize-none rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 py-1 text-[13px]"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send();
            }}
          />
          <div className="mt-1.5 flex justify-end gap-2">
            <button type="button" className={textButton} disabled={busy} onClick={() => onAct(setResolved(comment.id, !comment.done))}>
              {comment.done ? "Reopen" : "Resolve"}
            </button>
            <button type="button" className={textButton} disabled={busy || !draft.trim()} onClick={send}>
              Reply
            </button>
          </div>
        </div>
      )}
    </article>
  );
}

function Entry({ author, initials, date, text }: { author: string; initials: string; date: string; text: string }) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[10px] font-medium text-[var(--accent-ink)]">
          {(initials || author.slice(0, 1)).slice(0, 2)}
        </span>
        <span className="min-w-0 flex-1 truncate font-medium">{author}</span>
        {date && <span className="shrink-0 text-xs text-[var(--muted)]">{formatRunTime(date)}</span>}
      </div>
      <p className="mt-1 whitespace-pre-wrap break-words">{text}</p>
    </div>
  );
}
