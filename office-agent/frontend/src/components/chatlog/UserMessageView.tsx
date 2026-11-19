import { useContext, useState } from "react";
import { type LogItem } from "../../state/reducer";
import { CloseIcon, RewindIcon } from "../icons";
import { CopyButton } from "../CopyButton";
import { attachedFilesNote, attachmentKind, fileCards, type AttachmentView } from "../../lib/attachments";
import { MessageActionsContext, SteerActionsContext, ViewFile } from "./contexts";
import { AttachmentCard, AttachmentDialog } from "../Attachments";
import { ThreadIdContext } from "../threadContext";
import { HoverTip, MESSAGE_ICON_BUTTON } from "./HoverTip";
import { EditBox, SentMessageActions } from "./SentMessageActions";

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
      {fileCards(files, images).length > 0 && (
        <div className="flex flex-wrap justify-end gap-1.5">
          {fileCards(files, images).map((path) => {
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
              <CopyButton getText={() => item.text} title="" className={MESSAGE_ICON_BUTTON} />
            </HoverTip>
          )}
          <HoverTip label="Rewind is unavailable while working" align="end">
            <button type="button" aria-label="Rewind" disabled className={MESSAGE_ICON_BUTTON}>
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
              className={MESSAGE_ICON_BUTTON}
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

/** A sent message, with its time, Rewind, Edit and Copy under it while the pointer is on it. Both
 * Rewind and Edit take this message and every turn after it out of the conversation; Edit then
 * sends the new text as the latest message. */
export function UserMessageView({ item }: { item: Extract<LogItem, { kind: "user" }> }) {
  const actions = useContext(MessageActionsContext);
  const [editing, setEditing] = useState(false);
  // Read on hover, so "2 minutes ago" is current when it shows.
  const [now, setNow] = useState(() => Date.now());
  const files = item.files ?? [];
  const hasAttachments = files.length > 0 || (item.images?.length ?? 0) > 0;
  const [textExpanded, setTextExpanded] = useState(false);
  const isLongText = item.text.length > LONG_MESSAGE_COLLAPSE_CHARS;
  const shownText =
    isLongText && !textExpanded ? `${item.text.slice(0, LONG_MESSAGE_COLLAPSE_CHARS)}…` : item.text;
  const leavesChanges = actions?.leavesChanges.has(item.turnIndex) ?? false;

  if (editing && actions) {
    return (
      <EditBox
        text={item.text}
        blocked={actions.blocked}
        leavesChanges={leavesChanges}
        onCancel={() => setEditing(false)}
        onSave={(draft) => {
          setEditing(false);
          // The note naming the files goes back with the text: it is how the model knows them.
          actions.edit(item.turnIndex, files.length > 0 ? `${draft}\n\n${attachedFilesNote(files)}` : draft);
        }}
      />
    );
  }

  return (
    <div className="group/msg ml-auto flex max-w-[96%] flex-col items-end gap-1.5" onMouseEnter={() => setNow(Date.now())}>
      <SentAttachments files={files} images={item.images ?? []} />
      {(item.text.trim() !== "" || !hasAttachments) && (
        <div className="rounded-2xl bg-[var(--user-bubble)] px-4 py-2 text-[var(--user-bubble-fg)] whitespace-pre-wrap">
          {shownText}
        </div>
      )}
      {isLongText && (
        <button
          type="button"
          className="text-xs text-[var(--muted)] hover:text-[var(--fg)] hover:underline"
          onClick={() => setTextExpanded((prev) => !prev)}
        >
          {textExpanded ? "Show less" : "Show more"}
        </button>
      )}
      <SentMessageActions
        text={item.text}
        sentAt={item.sentAt}
        now={now}
        blocked={actions ? actions.blocked : undefined}
        leavesChanges={leavesChanges}
        onRewind={() => actions?.rewind(item.turnIndex, item.text)}
        onEdit={() => setEditing(true)}
      />
    </div>
  );
}
