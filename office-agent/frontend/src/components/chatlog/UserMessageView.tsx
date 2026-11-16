import { useContext, useState, type ReactNode } from "react";
import { type LogItem } from "../../state/reducer";
import { CloseIcon, PencilIcon, RewindIcon } from "../icons";
import { CopyButton } from "../CopyButton";
import { attachedFilesNote, attachmentKind, type AttachmentView } from "../../lib/attachments";
import { SteerActionsContext, ViewFile } from "./contexts";
import { AttachmentCard, AttachmentDialog } from "../Attachments";
import { ThreadIdContext } from "../threadContext";

/** A user bubble with a hover-revealed edit affordance -- clicking it
 * swaps the bubble for an inline textarea; submitting truncates the
 * conversation at this turn and regenerates from the edited text (see
 * EditMessageOut's docstring in wire.ts and _handle_edit_message_locked
 * in conversation/session.py for what happens server-side). Its own useState (not
 * lifted into ChatState) mirrors ToolCallRow/ToolRunGroupView's existing
 * pattern of local, ephemeral UI state that doesn't need to survive a
 * remount or be visible to any other component. */
// A user bubble past this length collapses behind "Show more" -- mainly
// hit by a pasted-content turn (Composer.tsx's submit() now puts the real
// pasted text in displayText instead of dropping it), where the raw text
// can otherwise be long enough to push the rest of the conversation off
// screen. Same magnitude as Composer's own PASTE_CARD_MIN_CHARS, so "long
// enough to collapse" means the same thing on both sides of a send.
const LONG_MESSAGE_COLLAPSE_CHARS = 1000;

/** The files and pictures sent with a message, as cards above its bubble; each opens a preview. */
function SentAttachments({ files, images }: { files: string[]; images: string[] }) {
  const threadId = useContext(ThreadIdContext);
  const viewFile = useContext(ViewFile);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [openFile, setOpenFile] = useState<AttachmentView | null>(null);
  return (
    <>
      {files.length > 0 && (
        <div className="flex flex-wrap justify-end gap-1.5">
          {files.map((path) => {
            const name = path.split(/[\\/]/).pop() ?? path;
            const view: AttachmentView = { kind: attachmentKind(name), name, path };
            // A Word, Excel or PowerPoint file opens in its panel; the rest in the preview.
            return <AttachmentCard key={path} view={view} threadId={threadId} onOpen={() => { if (!viewFile?.(path)) setOpenFile(view); }} />;
          })}
        </div>
      )}
      {images.length > 0 && (
        <div className="flex flex-wrap justify-end gap-1.5">
          {images.map((src, i) => (
            <button
              key={i}
              type="button"
              title="Preview image"
              className="h-16 w-16 cursor-zoom-in overflow-hidden rounded-lg border border-[var(--border)]"
              onClick={() => setLightboxSrc(src)}
            >
              <img src={src} alt={`Attachment ${i + 1}`} className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
      {openFile && <AttachmentDialog view={openFile} threadId={threadId} onClose={() => setOpenFile(null)} />}
      {lightboxSrc && (
        <AttachmentDialog
          view={{ kind: "image", name: "Attachment", src: lightboxSrc }}
          threadId={threadId}
          onClose={() => setLightboxSrc(null)}
        />
      )}
    </>
  );
}

/** A dark label above a control while the pointer is on it. It sits on a wrapper rather than the
 * button, so a disabled button still says why it is disabled. */
function HoverTip({ label, align = "center", children }: { label: string; align?: "center" | "end"; children: ReactNode }) {
  return (
    <span className="group/tip relative inline-flex">
      {children}
      <span
        role="tooltip"
        className={`pointer-events-none absolute bottom-full z-20 mb-1.5 whitespace-nowrap rounded-md bg-[var(--primary)] px-2 py-1 text-xs text-[var(--primary-fg)] opacity-0 shadow-md transition-opacity delay-150 group-hover/tip:opacity-100 ${
          align === "end" ? "right-0" : "left-1/2 -translate-x-1/2"
        }`}
      >
        {label}
      </span>
    </span>
  );
}

const STEER_ICON_BUTTON =
  "flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-[var(--muted)]";

/** A note added while the reply was being worked on: a user bubble, with
 * whether the model has read it yet. */
export function SteerView({ item }: { item: Extract<LogItem, { kind: "steer" }> }) {
  const actions = useContext(SteerActionsContext);
  const files = item.files ?? [];
  const images = item.images ?? [];
  // Taking the note back puts it in the message box, which would lose what is typed there.
  const editBlocked = actions?.composerHasDraft ?? false;
  return (
    <div className="ml-auto flex max-w-[96%] flex-col items-end gap-1">
      <div className={`flex flex-col items-end gap-1.5 ${item.status === "pending" ? "opacity-60" : ""}`}>
        <SentAttachments files={files} images={images} />
        {(item.text.trim() !== "" || (files.length === 0 && images.length === 0)) && (
          <div className="rounded-2xl bg-[var(--user-bubble)] px-4 py-2 text-[var(--user-bubble-fg)] whitespace-pre-wrap">
            {item.text}
          </div>
        )}
      </div>
      {item.status === "pending" && actions ? (
        <div className="flex items-center gap-0.5 text-xs text-[var(--muted)]">
          {item.text.trim() !== "" && (
            <HoverTip label="Copy">
              <CopyButton getText={() => item.text} title="" className={STEER_ICON_BUTTON} />
            </HoverTip>
          )}
          <HoverTip label="Rewind is unavailable while working" align="end">
            <button type="button" aria-label="Rewind" disabled className={STEER_ICON_BUTTON}>
              <RewindIcon className="h-3.5 w-3.5" />
            </button>
          </HoverTip>
          <HoverTip
            label={editBlocked ? "Clear the message box first to edit this message" : "Cancel and edit message"}
            align="end"
          >
            <button
              type="button"
              aria-label="Cancel and edit message"
              disabled={editBlocked}
              className={STEER_ICON_BUTTON}
              onClick={() => actions.withdraw(item.id)}
            >
              <CloseIcon className="h-3.5 w-3.5" />
            </button>
          </HoverTip>
          <button
            type="button"
            aria-label="Interrupt the reply and send this now"
            className="ml-0.5 rounded-md px-2 py-1 text-[var(--muted)] hover:bg-[color-mix(in_srgb,var(--fg)_10%,transparent)] hover:text-[var(--fg)]"
            onClick={actions.sendNow}
          >
            Send now
          </button>
        </div>
      ) : (
        <span className="text-xs text-[var(--muted)]">
          {item.status === "pending" ? "Will be read at the next step" : "Added while working"}
        </span>
      )}
    </div>
  );
}

export function UserMessageView({
  item,
  onEditMessage,
}: {
  item: Extract<LogItem, { kind: "user" }>;
  onEditMessage?: (turnIndex: number, text: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.text);
  const files = item.files ?? [];
  const hasAttachments = files.length > 0 || (item.images?.length ?? 0) > 0;
  const [textExpanded, setTextExpanded] = useState(false);
  const isLongText = item.text.length > LONG_MESSAGE_COLLAPSE_CHARS;
  const shownText =
    isLongText && !textExpanded ? `${item.text.slice(0, LONG_MESSAGE_COLLAPSE_CHARS)}…` : item.text;

  const cancel = () => {
    setDraft(item.text);
    setEditing(false);
  };

  const submit = () => {
    if (!draft.trim() || !onEditMessage) return;
    // The note naming the files goes back with the text: it is how the model knows them.
    onEditMessage(item.turnIndex, files.length > 0 ? `${draft}\n\n${attachedFilesNote(files)}` : draft);
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="ml-auto flex max-w-[96%] flex-col items-end gap-1.5">
        <textarea
          autoFocus
          className="w-full resize-none rounded-2xl border border-[var(--accent)] bg-[var(--user-bubble)] px-4 py-2 text-[var(--user-bubble-fg)] outline-none"
          rows={Math.min(10, draft.split("\n").length)}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              cancel();
            } else if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              submit();
            }
          }}
        />
        <div className="flex gap-1.5">
          <button
            type="button"
            className="rounded-md border border-[var(--border)] px-2.5 py-1 text-xs hover:bg-[var(--card-bg)]"
            onClick={cancel}
          >
            Cancel
          </button>
          <button
            type="button"
            className="rounded-md bg-[var(--accent)] px-2.5 py-1 text-xs text-[var(--accent-fg)] disabled:opacity-40"
            onClick={submit}
            disabled={!draft.trim()}
          >
            Save &amp; submit
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="ml-auto flex max-w-[96%] flex-col items-end gap-1.5">
      <SentAttachments files={files} images={item.images ?? []} />
      <div className="group/msg flex items-center gap-1">
        {onEditMessage && (
          <button
            type="button"
            title="Edit message"
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[var(--muted)] opacity-0 transition-opacity hover:bg-[var(--card-bg)] hover:text-[var(--fg)] group-hover/msg:opacity-100"
            onClick={() => setEditing(true)}
          >
            <PencilIcon className="h-3.5 w-3.5" />
          </button>
        )}
        {(item.text.trim() !== "" || !hasAttachments) && (
          <div className="rounded-2xl bg-[var(--user-bubble)] px-4 py-2 text-[var(--user-bubble-fg)] whitespace-pre-wrap">
            {shownText}
          </div>
        )}
      </div>
      {isLongText && (
        <button
          type="button"
          className="text-xs text-[var(--muted)] hover:text-[var(--fg)] hover:underline"
          onClick={() => setTextExpanded((prev) => !prev)}
        >
          {textExpanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}
