import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { createPortal } from "react-dom";
import {
  addComment,
  commentMessage,
  commentPlace,
  deleteComment,
  elementAt,
  getComments,
  replyToComment,
  resolveComment,
  type CommentLink,
  type SlideComment,
  type SlideElement,
} from "../../lib/slideComments";
import type { SlideInfo } from "../../lib/slides";
import { ArrowUpIcon, CheckIcon, TrashIcon } from "../icons";

/** While a sent comment waits for coscribe's answer, the panel looks for it this often. */
const ANSWER_POLL_MS = 5000;
const POPOVER_WIDTH = 360;
// About the tallest a thread card gets before it scrolls; it is moved up to fit above this.
const POPOVER_HEIGHT = 380;

const slideId = (slide: SlideInfo) => slide.name.replace(/\.[^.]+$/, "");

/** The deck's comments, kept fresh while an answer from coscribe is on its way. */
export function useSlideComments(threadId: string, path: string, refreshKey: string) {
  const [comments, setComments] = useState<SlideComment[]>([]);
  const [failed, setFailed] = useState<string | null>(null);
  const refresh = useCallback(
    () =>
      getComments(threadId, path).then(
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
  const act = (job: Promise<unknown>) =>
    job.then(refresh, (e: unknown) => setFailed(`The comment could not be saved: ${e instanceof Error ? e.message : String(e)}`));
  return { comments, failed, refresh, act };
}

/** `slide` is where the slide sat on screen when the card opened, for placing the card. */
type Opened =
  { kind: "new"; x: number; y: number; element: SlideElement | null; slide: DOMRect } | { kind: "thread"; id: string; slide: DOMRect };

/** Opens the new comment the editor's bar asks for; the returned ref goes on an element inside
 * the slide, which gives the slide's place on screen. */
function useOpenFromBar(startAt: CommentStart | null | undefined, setOpened: (opened: Opened) => void) {
  const layerRef = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const slideBox = layerRef.current?.parentElement?.getBoundingClientRect();
    if (!startAt || !slideBox) return;
    const { x, y, element, box } = startAt;
    setOpened({ kind: "new", x, y, element: { id: "", label: element, box }, slide: slideBox });
  }, [startAt, setOpened]);
  return layerRef;
}

/** A new comment on an element: where (fractions of the slide) and its label. */
export interface CommentStart {
  x: number;
  y: number;
  element: string;
  box: [number, number, number, number];
}

/** Over the slide: the element under the pointer in comment mode, a marker per comment, the box
 * for a new one and an opened thread. */
export function SlideComments({
  threadId,
  path,
  deckName,
  slide,
  slideNumber,
  store,
  commenting,
  showResolved,
  onSend,
  startAt,
}: {
  threadId: string;
  path: string;
  deckName: string;
  slide: SlideInfo;
  slideNumber: number;
  store: ReturnType<typeof useSlideComments>;
  commenting: boolean;
  showResolved: boolean;
  /** Absent where there is no conversation to send to. */
  onSend?: (text: string, link: CommentLink) => void;
  /** A new comment to open, from the editor's bar. */
  startAt?: CommentStart | null;
}) {
  const [hover, setHover] = useState<SlideElement | null>(null);
  const [opened, setOpened] = useState<Opened | null>(null);
  const layerRef = useOpenFromBar(startAt, setOpened);
  const here = store.comments.filter((c) => c.slide === slideId(slide) && (showResolved || !c.resolved));
  useEffect(() => setOpened(null), [slide.name]);

  const point = (e: PointerEvent<HTMLDivElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    return { x: (e.clientX - box.left) / box.width, y: (e.clientY - box.top) / box.height };
  };
  const thread = opened?.kind === "thread" ? store.comments.find((c) => c.id === opened.id) : undefined;

  return (
    <>
      <span ref={layerRef} hidden />
      {commenting && (
        <div
          aria-label="Click to comment"
          className="absolute inset-0 cursor-crosshair"
          onPointerMove={(e) => {
            const { x, y } = point(e);
            setHover(elementAt(slide.elements, x, y));
          }}
          onPointerLeave={() => setHover(null)}
          onClick={(e) => {
            const { x, y } = point(e as unknown as PointerEvent<HTMLDivElement>);
            setOpened({ kind: "new", x, y, element: elementAt(slide.elements, x, y), slide: e.currentTarget.getBoundingClientRect() });
          }}
        />
      )}
      {commenting && hover && <ElementOutline element={hover} />}
      {opened?.kind === "new" && opened.element && <ElementOutline element={opened.element} />}
      {here.map((comment) => (
        <CommentPin key={comment.id} comment={comment} onOpen={(at) => setOpened({ kind: "thread", id: comment.id, slide: at })} />
      ))}
      {opened?.kind === "new" && (
        <Popover x={opened.x} y={opened.y} slide={opened.slide} onClose={() => setOpened(null)}>
          <NewComment
            place={commentPlace(slideNumber, opened.element?.label ?? "")}
            canSend={onSend !== undefined}
            onCancel={() => setOpened(null)}
            onPost={(text, send) => {
              const element = opened.element?.label ?? "";
              const made = addComment(threadId, { path, slide: slideId(slide), x: opened.x, y: opened.y, element, text, sent: send });
              void store.act(
                made.then((comment) => {
                  if (send) onSend?.(commentMessage(deckName, slideNumber, slide.name, element, text), { path, commentId: comment.id });
                }),
              );
              setOpened(null);
            }}
          />
        </Popover>
      )}
      {thread && opened && (
        <Popover x={thread.x} y={thread.y} slide={opened.slide} onClose={() => setOpened(null)}>
          <Thread
            comment={thread}
            place={commentPlace(slideNumber, thread.element)}
            onReply={(text) => void store.act(replyToComment(threadId, path, thread.id, text))}
            onResolve={() => {
              void store.act(resolveComment(threadId, path, thread.id, !thread.resolved));
              setOpened(null);
            }}
            onDelete={() => {
              void store.act(deleteComment(threadId, path, thread.id));
              setOpened(null);
            }}
            onClose={() => setOpened(null)}
          />
        </Popover>
      )}
    </>
  );
}

/** A comment's marker: its author's initial in a speech-bubble shape, its corner on the point. */
function CommentPin({ comment, onOpen }: { comment: SlideComment; onOpen: (slide: DOMRect) => void }) {
  return (
    <button
      type="button"
      aria-label={`Comment by ${comment.author}: ${comment.text}`}
      className={`absolute z-[5] flex h-7 w-7 -translate-y-full items-center justify-center rounded-full rounded-bl-none border-2 border-white text-xs font-semibold text-white shadow ${comment.resolved ? "bg-[var(--muted)]" : "bg-[var(--accent)]"}`}
      style={{ left: `${comment.x * 100}%`, top: `${comment.y * 100}%` }}
      onClick={(e) => {
        e.stopPropagation();
        const slide = e.currentTarget.parentElement?.getBoundingClientRect();
        if (slide) onOpen(slide);
      }}
    >
      {comment.author.charAt(0).toUpperCase()}
    </button>
  );
}

function ElementOutline({ element }: { element: SlideElement }) {
  const [x, y, w, h] = element.box;
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute rounded-[2px] outline outline-2 outline-[var(--accent)]"
      style={{ left: `${x * 100}%`, top: `${y * 100}%`, width: `${w * 100}%`, height: `${h * 100}%` }}
    />
  );
}

/** A card beside the point, on whichever side has room, kept inside the window: the panel can
 * be narrower than the card, so it is drawn above everything rather than inside the slide. */
function Popover({ x, y, slide, onClose, children }: { x: number; y: number; slide: DOMRect; onClose: () => void; children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  // A click anywhere outside the card, or Escape, closes it.
  useEffect(() => {
    const away = (e: Event) => {
      if (e.target instanceof Node && !ref.current?.contains(e.target)) onClose();
    };
    const escape = (e: globalThis.KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("pointerdown", away);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", away);
      document.removeEventListener("keydown", escape);
    };
  }, [onClose]);
  const px = slide.left + x * slide.width;
  const py = slide.top + y * slide.height;
  const room = window.innerWidth - 8;
  const right = px + 14 + POPOVER_WIDTH <= room;
  const left = Math.max(8, Math.min(room - POPOVER_WIDTH, right ? px + 14 : px - 14 - POPOVER_WIDTH));
  const top = Math.max(8, Math.min(window.innerHeight - POPOVER_HEIGHT, py));
  return createPortal(
    <div
      ref={ref}
      className="fixed z-50 rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-3.5 shadow-[0_8px_28px_rgba(0,0,0,0.16)]"
      style={{ left, top, width: Math.min(POPOVER_WIDTH, room - 8) }}
      onClick={(e) => e.stopPropagation()}
    >
      {children}
    </div>,
    document.body,
  );
}

function NewComment({
  place,
  canSend,
  onCancel,
  onPost,
}: {
  place: string;
  canSend: boolean;
  onCancel: () => void;
  onPost: (text: string, send: boolean) => void;
}) {
  const [text, setText] = useState("");
  const [send, setSend] = useState(canSend);
  const post = () => {
    if (text.trim()) onPost(text.trim(), send);
  };
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    e.stopPropagation();
    if (e.key === "Escape") onCancel();
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      post();
    }
  };
  return (
    <>
      <div className="truncate pb-2 text-[13px] text-[var(--muted)]">{place}</div>
      {send && (
        <span className="mb-1.5 inline-block rounded-md bg-[var(--accent-soft)] px-1.5 py-0.5 text-sm text-[var(--accent-ink)]">
          @coscribe
        </span>
      )}
      <textarea
        autoFocus
        rows={2}
        value={text}
        aria-label="Comment"
        placeholder="Add a comment"
        className="w-full resize-none bg-transparent text-[15px] text-[var(--fg)] outline-none placeholder:text-[var(--muted)]"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
      />
      <div className="flex items-center gap-2 pt-1.5">
        {canSend && (
          <label className="flex cursor-pointer items-center gap-2 text-sm text-[var(--fg)]">
            <input type="checkbox" checked={send} className="h-4 w-4 accent-[var(--accent)]" onChange={(e) => setSend(e.target.checked)} />
            Send to Coscribe
          </label>
        )}
        <div className="flex-1" />
        <button
          type="button"
          aria-label="Post comment"
          title="Post (Enter)"
          disabled={!text.trim()}
          className="flex h-7 w-7 items-center justify-center rounded-full text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)] disabled:opacity-40"
          onClick={post}
        >
          <ArrowUpIcon className="h-4 w-4" />
        </button>
      </div>
    </>
  );
}

function Thread({
  comment,
  place,
  onReply,
  onResolve,
  onDelete,
  onClose,
}: {
  comment: SlideComment;
  place: string;
  onReply: (text: string) => void;
  onResolve: () => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  const [reply, setReply] = useState("");
  const waiting = comment.sent && !comment.replies.some((r) => r.author === "coscribe");
  const iconButton =
    "flex h-7 w-7 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]";
  return (
    <>
      <div className="flex items-center gap-1 pb-2">
        <span className="min-w-0 flex-1 truncate text-[13px] text-[var(--muted)]">{place}</span>
        <button
          type="button"
          className={iconButton}
          title={comment.resolved ? "Reopen" : "Resolve"}
          aria-label={comment.resolved ? "Reopen" : "Resolve"}
          onClick={onResolve}
        >
          <CheckIcon className="h-4 w-4" />
        </button>
        <button type="button" className={iconButton} title="Delete" aria-label="Delete comment" onClick={onDelete}>
          <TrashIcon className="h-4 w-4" />
        </button>
      </div>
      <div className="max-h-[260px] space-y-2.5 overflow-auto">
        {[{ author: comment.author, text: comment.text }, ...comment.replies].map((entry, i) => (
          <div key={i}>
            <div className="text-[13px] font-semibold text-[var(--fg)]">{entry.author}</div>
            <div className="whitespace-pre-wrap text-sm text-[var(--fg)]">{entry.text}</div>
          </div>
        ))}
        {waiting && <div className="text-[13px] text-[var(--muted)]">Sent to Coscribe; its answer appears here.</div>}
      </div>
      <input
        value={reply}
        aria-label="Reply"
        placeholder="Reply"
        className="mt-2.5 h-8 w-full rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-2.5 text-sm text-[var(--fg)] outline-none"
        onChange={(e) => setReply(e.target.value)}
        onKeyDown={(e) => {
          e.stopPropagation();
          if (e.key === "Escape") onClose();
          if (e.key === "Enter" && reply.trim()) {
            onReply(reply.trim());
            setReply("");
          }
        }}
      />
    </>
  );
}
