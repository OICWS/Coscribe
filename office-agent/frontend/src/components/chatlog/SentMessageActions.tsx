import { useState } from "react";
import { fullTime } from "../../lib/messageActions";
import { timeAgo } from "../../lib/sessionList";
import { CopyButton } from "../CopyButton";
import { AlertCircleIcon, PencilIcon, RewindIcon } from "../icons";
import { HoverTip, MESSAGE_ICON_BUTTON } from "./HoverTip";

const LEAVES_CHANGES = " Files changed and commands run after it stay as they are.";
const REWIND_TAKES_OUT = "Takes this message and everything after it out of the conversation.";
const EDIT_RESTARTS = "Saving sends this as your latest message and restarts from here.";

/** The row under a sent message: when it was sent, Rewind and Edit (absent where `blocked` is
 * undefined, disabled with the reason where it is a string) and Copy. `leavesChanges` adds to
 * their tooltips that what later turns did outside the conversation stays. */
export function SentMessageActions({
  text,
  sentAt,
  now,
  blocked,
  leavesChanges,
  onRewind,
  onEdit,
}: {
  text: string;
  sentAt?: string;
  now: number;
  blocked: string | null | undefined;
  leavesChanges: boolean;
  onRewind: () => void;
  onEdit: () => void;
}) {
  return (
    <div className="flex items-center gap-0.5 text-xs text-[var(--muted)] opacity-0 transition-opacity focus-within:opacity-100 group-hover/msg:opacity-100">
      {sentAt && (
        <HoverTip below label={fullTime(sentAt)}>
          <span className="mr-1 cursor-default">{timeAgo(sentAt, now)}</span>
        </HoverTip>
      )}
      {blocked !== undefined && (
        <>
          <HoverTip below label={blocked ?? "Rewind to here"} detail={blocked ? undefined : REWIND_TAKES_OUT + (leavesChanges ? LEAVES_CHANGES : "")}>
            <button type="button" aria-label="Rewind to here" disabled={blocked !== null} className={MESSAGE_ICON_BUTTON} onClick={onRewind}>
              <RewindIcon className="h-3.5 w-3.5" />
            </button>
          </HoverTip>
          <HoverTip below label={blocked ?? "Edit"} detail={blocked ? undefined : EDIT_RESTARTS + (leavesChanges ? LEAVES_CHANGES : "")} align="end">
            <button type="button" aria-label="Edit" disabled={blocked !== null} className={MESSAGE_ICON_BUTTON} onClick={onEdit}>
              <PencilIcon className="h-3.5 w-3.5" />
            </button>
          </HoverTip>
        </>
      )}
      {text.trim() !== "" && (
        <HoverTip below label="Copy" align="end">
          <CopyButton getText={() => text} title="" className={MESSAGE_ICON_BUTTON} />
        </HoverTip>
      )}
    </div>
  );
}

/** A sent message being edited in place; Save is offered once the text changed. */
export function EditBox({
  text,
  blocked,
  leavesChanges,
  onCancel,
  onSave,
}: {
  text: string;
  blocked: string | null;
  leavesChanges: boolean;
  onCancel: () => void;
  onSave: (draft: string) => void;
}) {
  const [draft, setDraft] = useState(text);
  const canSave = draft.trim() !== "" && draft !== text && blocked === null;
  const save = () => {
    if (canSave) onSave(draft);
  };
  return (
    <div className="ml-auto flex w-full max-w-[96%] flex-col items-end gap-1.5">
      <textarea
        autoFocus
        aria-label="Edit message"
        className="w-full max-w-[640px] resize-none rounded-2xl border border-[var(--accent)] bg-[var(--bg)] px-4 py-2 text-[var(--fg)] outline-none"
        rows={Math.min(10, Math.max(1, draft.split("\n").length))}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            onCancel();
          } else if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault();
            save();
          }
        }}
      />
      <div className="flex items-center gap-1.5 text-sm">
        <HoverTip label={EDIT_RESTARTS + (leavesChanges ? LEAVES_CHANGES : "")} align="end">
          <span className="flex h-7 w-7 items-center justify-center text-[var(--muted)]">
            <AlertCircleIcon className="h-4 w-4 rotate-180" />
          </span>
        </HoverTip>
        <button type="button" className="rounded-md px-2.5 py-1 hover:bg-[var(--card-bg)]" onClick={onCancel}>
          Cancel
        </button>
        <HoverTip label={blocked ?? "Save"} align="end">
          <button
            type="button"
            className="rounded-md bg-[var(--primary)] px-2.5 py-1 text-[var(--primary-fg)] disabled:bg-[var(--card-bg)] disabled:text-[var(--muted)]"
            onClick={save}
            disabled={!canSave}
          >
            Save
          </button>
        </HoverTip>
      </div>
    </div>
  );
}
