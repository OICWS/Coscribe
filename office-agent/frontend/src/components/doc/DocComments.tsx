import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { getDocComments, type DocComment } from "../../lib/docComments";
import { CloseIcon, FilterIcon, MoreIcon } from "../icons";
import { PanelCommentButton } from "../artifacts/PanelCommentButton";
import { SlideMenu, type MenuEntry } from "../slides/SlideMenu";

/** While a sent comment waits for coscribe's answer, the panel looks for it this often. */
const ANSWER_POLL_MS = 5000;

/** The Doc's comments, kept fresh while an answer from coscribe is on its way. */
export function useDocComments(threadId: string, path: string, refreshKey: string) {
  const [comments, setComments] = useState<DocComment[]>([]);
  const [failed, setFailed] = useState<string | null>(null);
  const refresh = useCallback(
    () =>
      getDocComments(threadId, path).then(
        (loaded) => {
          setComments(loaded);
          setFailed(null);
        },
        (e: unknown) => setFailed(`Comments could not be read: ${e instanceof Error ? e.message : String(e)}`),
      ),
    [threadId, path],
  );
  useEffect(() => {
    void refresh();
  }, [refresh, refreshKey]);
  const waiting = comments.some((c) => c.sent && !c.resolved && !c.replies.some((r) => r.author === "coscribe"));
  useEffect(() => {
    if (!waiting) return;
    const timer = setInterval(() => void refresh(), ANSWER_POLL_MS);
    return () => clearInterval(timer);
  }, [waiting, refresh]);
  const act = useCallback((job: Promise<unknown>) => job.then(refresh, (e: unknown) => setFailed(`The comment could not be saved: ${e instanceof Error ? e.message : String(e)}`)), [refresh]);
  return { comments, failed, refresh, act };
}

type Filter = "open" | "resolved" | "all";
const FILTERS: { value: Filter; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "resolved", label: "Resolved" },
  { value: "all", label: "All" },
];

const time = (iso: string) => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

function Avatar({ name }: { name: string }) {
  return (
    <span aria-hidden className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-[11px] font-medium text-white">
      {(name[0] ?? "?").toUpperCase()}
    </span>
  );
}

const ghost = "rounded-md px-2 py-1 text-xs text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]";

function EditForm({ text, onChange, onCancel, onSave }: { text: string; onChange: (text: string) => void; onCancel: () => void; onSave: () => void }) {
  return (
    <form
      className="mt-1.5"
      onSubmit={(e) => {
        e.preventDefault();
        onSave();
      }}
    >
      <textarea
        autoFocus
        aria-label="Edit comment"
        value={text}
        rows={3}
        className="w-full resize-none rounded-lg border border-[var(--border)] bg-[var(--field-bg)] p-2 text-sm outline-none focus:border-[var(--focus)]"
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="mt-1 flex justify-end gap-1">
        <button type="button" className={ghost} onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="rounded-md bg-[var(--primary)] px-2.5 py-1 text-xs text-[var(--primary-fg)] hover:bg-[var(--primary-hover)]">
          Save
        </button>
      </div>
    </form>
  );
}

function Card({
  comment,
  focused,
  hint,
  onResolve,
  onReply,
  onEdit,
  onDelete,
}: {
  comment: DocComment;
  focused: boolean;
  hint: string;
  onResolve: (resolved: boolean) => void;
  onReply: (text: string) => void;
  onEdit: (text: string) => void;
  onDelete: () => void;
}) {
  const [menu, setMenu] = useState<DOMRect | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (focused) ref.current?.scrollIntoView({ block: "nearest" });
  }, [focused]);
  const entries: MenuEntry[] = [
    { label: "Edit", onSelect: () => setEditing(comment.text) },
    { label: "Delete", danger: true, onSelect: onDelete },
  ];
  const answered = comment.replies.some((r) => r.author === "coscribe");
  return (
    <div ref={ref} className={`border-b border-[var(--border)] px-4 py-3 last:border-b-0 ${focused ? "bg-[var(--accent-soft)]" : ""}`} data-comment={comment.id}>
      <div className="mb-2 truncate border-l-2 border-[var(--border-hover)] pl-2 text-xs text-[var(--muted)]">{comment.detached ? "The text this was on is gone" : hint}</div>
      <div className="flex items-center gap-2">
        <Avatar name={comment.author} />
        <span className="text-sm font-medium">{comment.author}</span>
        <span className="text-xs text-[var(--muted)]">{time(comment.created)}</span>
        <div className="flex-1" />
        <button
          type="button"
          aria-label="Comment options"
          aria-haspopup="menu"
          className="flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)]"
          onClick={(e) => setMenu(e.currentTarget.getBoundingClientRect())}
        >
          <MoreIcon className="h-4 w-4" />
        </button>
      </div>
      {editing === null ? (
        <p className="mt-1.5 whitespace-pre-wrap text-sm">{comment.text}</p>
      ) : (
        <EditForm
          text={editing}
          onChange={setEditing}
          onCancel={() => setEditing(null)}
          onSave={() => {
            if (editing.trim()) onEdit(editing.trim());
            setEditing(null);
          }}
        />
      )}
      {comment.replies.map((r, i) => (
        <div key={i} className="mt-2 flex gap-2">
          <Avatar name={r.author} />
          <div className="min-w-0 flex-1">
            <div className="text-xs">
              <span className="font-medium">{r.author}</span> <span className="text-[var(--muted)]">{time(r.created)}</span>
            </div>
            <p className="whitespace-pre-wrap text-sm">{r.text}</p>
          </div>
        </div>
      ))}
      {comment.sent && !comment.resolved && !answered && <div className="mt-2 text-xs text-[var(--muted)]">Waiting for coscribe…</div>}
      {!comment.sent && !comment.resolved && <div className="mt-2 text-xs text-[var(--muted)]">Not sent to coscribe yet</div>}
      <form
        className="mt-2 flex items-center gap-1"
        onSubmit={(e) => {
          e.preventDefault();
          if (!reply.trim()) return;
          onReply(reply.trim());
          setReply("");
        }}
      >
        <input
          aria-label="Reply"
          placeholder="Reply"
          value={reply}
          className="h-7 min-w-0 flex-1 rounded-md border border-[var(--border)] bg-[var(--field-bg)] px-2 text-xs outline-none focus:border-[var(--focus)]"
          onChange={(e) => setReply(e.target.value)}
        />
        <button type="button" className={ghost} onClick={() => onResolve(!comment.resolved)}>
          {comment.resolved ? "Reopen" : "Resolve"}
        </button>
      </form>
      {menu && <SlideMenu anchor={menu} label="Comment" width={150} entries={entries} onClose={() => setMenu(null)} />}
    </div>
  );
}

/** The comments of the Doc beside the page: filtered, each answerable, resolvable, editable and deletable;
 * the comments not yet sent to coscribe can go in one message. */
export function CommentsPopover({
  comments,
  focus,
  hintFor,
  onSendUnsent,
  onResolve,
  onReply,
  onEdit,
  onDelete,
  onClose,
}: {
  comments: DocComment[];
  focus: string | null;
  /** The words a comment is on, or the start of its block. */
  hintFor: (comment: DocComment) => string;
  /** Absent where there is no conversation to send to. */
  onSendUnsent?: (unsent: DocComment[]) => void;
  onResolve: (id: string, resolved: boolean) => void;
  onReply: (id: string, text: string) => void;
  onEdit: (id: string, text: string) => void;
  onDelete: (id: string) => void;
  onClose: () => void;
}) {
  const [filter, setFilter] = useState<Filter>("open");
  const [menu, setMenu] = useState<DOMRect | null>(null);
  const shown = comments.filter((c) => filter === "all" || (filter === "open" ? !c.resolved : c.resolved));
  const unsent = comments.filter((c) => !c.sent && !c.resolved);
  return (
    <div
      role="dialog"
      aria-label="Comments"
      className="absolute right-3 top-3 z-20 flex max-h-[min(70vh,560px)] w-[360px] max-w-[calc(100%-1.5rem)] flex-col rounded-xl border border-[var(--border)] bg-[var(--bg)] shadow-[0_8px_28px_rgba(0,0,0,0.12)]"
    >
      <div className="flex items-center gap-2 border-b border-[var(--border)] px-4 py-3">
        <span className="text-sm font-medium">Comments</span>
        <span className="text-sm text-[var(--muted)]">{comments.filter((c) => !c.resolved).length}</span>
        <div className="flex-1" />
        <button
          type="button"
          aria-label="Filter comments"
          aria-haspopup="menu"
          title={FILTERS.find((f) => f.value === filter)?.label}
          className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-[var(--card-bg)]"
          onClick={(e) => setMenu(e.currentTarget.getBoundingClientRect())}
        >
          <FilterIcon className="h-4 w-4" />
        </button>
        <button type="button" aria-label="Close comments" className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-[var(--card-bg)]" onClick={onClose}>
          <CloseIcon className="h-4 w-4" />
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {shown.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-[var(--muted)]">{filter === "resolved" ? "No resolved comments." : "No comments yet. Select some words to add one."}</div>
        )}
        {shown.map((comment) => (
          <Card
            key={comment.id}
            comment={comment}
            focused={comment.id === focus}
            hint={hintFor(comment)}
            onResolve={(resolved) => onResolve(comment.id, resolved)}
            onReply={(text) => onReply(comment.id, text)}
            onEdit={(text) => onEdit(comment.id, text)}
            onDelete={() => onDelete(comment.id)}
          />
        ))}
      </div>
      {onSendUnsent && unsent.length > 0 && (
        <div className="border-t border-[var(--border)] p-3">
          <button type="button" className="h-8 w-full rounded-lg bg-[var(--primary)] text-sm text-[var(--primary-fg)] hover:bg-[var(--primary-hover)]" onClick={() => onSendUnsent(unsent)}>
            Send {unsent.length} to coscribe
          </button>
        </div>
      )}
      {menu && (
        <SlideMenu
          anchor={menu}
          label="Show comments"
          width={150}
          entries={FILTERS.map((f) => ({ label: f.label, checked: filter === f.value, onSelect: () => setFilter(f.value) }))}
          onClose={() => setMenu(null)}
        />
      )}
    </div>
  );
}

/** The toggle in the panel's header: all the Doc's comments, with a dot while some are open. */
export function CommentsToggle({ shown, dot, onToggle }: { shown: boolean; dot: boolean; onToggle: () => void }) {
  const [slot, setSlot] = useState<HTMLElement | null>(null);
  const [menu, setMenu] = useState<DOMRect | null>(null);
  useEffect(() => setSlot(document.getElementById("doc-comments-toggle")), []);
  return slot
    ? createPortal(
        <>
          <PanelCommentButton pressed={shown} dot={dot} title="Show all comments" onToggle={onToggle} onMenu={setMenu} />
          {menu && (
            <SlideMenu
              anchor={menu}
              label="Comments"
              width={220}
              entries={[{ label: "Show all comments", checked: shown, onSelect: onToggle }, { note: "To comment, select some words." }]}
              onClose={() => setMenu(null)}
            />
          )}
        </>,
        slot,
      )
    : null;
}
