import { useEffect, useId, useState } from "react";
import { createPortal } from "react-dom";
import { exportFailedTurn, exportThread, type FailedTurn, listFailedTurns } from "../lib/rest";
import { saveBlob } from "../lib/slides";
import type { ThreadSummary } from "../types/session";
import { DownloadIcon } from "./icons";
import { itemClass } from "./menuStyle";

const FIELD =
  "w-full resize-none rounded-md border border-[var(--border)] bg-[var(--card-bg)] px-2 py-1.5 text-sm outline-none focus:border-[var(--accent)]";

function when(started: string): string {
  const date = new Date(started);
  return Number.isNaN(date.getTime()) ? started : date.toLocaleString();
}

function howItEnded(turn: FailedTurn): string {
  const failed = Object.entries(turn.turn.tools ?? {}).filter(([, count]) => count.errors > 0);
  const tools = failed.length ? `${failed.map(([name]) => name).join(", ")} failed` : "";
  if (turn.turn.outcome === "error") {
    const ended = `Ended on an error${turn.turn.error ? ` (${turn.turn.error})` : ""}`;
    return tools ? `${ended}; ${tools}` : ended;
  }
  if (turn.turn.outcome === "stopped") return tools ? `Stopped; ${tools}` : "Stopped";
  return tools || "Completed";
}

function TurnForm({
  turns,
  started,
  onPick,
  asked,
  onAsked,
  wentWrong,
  onWentWrong,
  preview,
}: {
  turns: FailedTurn[];
  started: string;
  onPick: (started: string) => void;
  asked: string;
  onAsked: (text: string) => void;
  wentWrong: string;
  onWentWrong: (text: string) => void;
  preview: string;
}) {
  return (
    <>
      <fieldset className="flex max-h-40 flex-col gap-1 overflow-y-auto">
        <legend className="mb-1 text-xs text-[var(--muted)]">Turn</legend>
        {turns.map((t) => (
          <label key={t.turn.started} className="flex cursor-pointer items-start gap-2 text-sm">
            <input
              type="radio"
              name="failed-turn"
              className="mt-1 accent-[var(--accent)]"
              checked={t.turn.started === started}
              onChange={() => onPick(t.turn.started)}
            />
            <span>
              {when(t.turn.started)}
              <span className="text-[var(--muted)]"> · {howItEnded(t)}</span>
            </span>
          </label>
        ))}
      </fieldset>
      <label className="flex flex-col gap-1 text-xs text-[var(--muted)]">
        What did you ask for? Optional, in your own words.
        <textarea rows={2} className={FIELD} value={asked} onChange={(e) => onAsked(e.target.value)} />
      </label>
      <label className="flex flex-col gap-1 text-xs text-[var(--muted)]">
        What went wrong? Optional.
        <textarea rows={2} className={FIELD} value={wentWrong} onChange={(e) => onWentWrong(e.target.value)} />
      </label>
      <details className="text-xs text-[var(--muted)]">
        <summary className="cursor-pointer">The whole file</summary>
        <pre
          data-testid="failed-turn-preview"
          className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-[var(--card-bg)] p-2 text-[var(--fg)]"
        >
          {preview}
        </pre>
      </details>
    </>
  );
}

/** The person picks one failed turn of a conversation, sees the whole file it becomes and saves
 * it (decision 0052). Pressing Save is the consent: nothing is sent anywhere, the file goes where
 * they save it, and holds none of the conversation's words unless they write their own. */
export function FailedTurnDialog({ threadId, onClose }: { threadId: string; onClose: () => void }) {
  const titleId = useId();
  const [turns, setTurns] = useState<FailedTurn[] | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [started, setStarted] = useState("");
  const [asked, setAsked] = useState("");
  const [wentWrong, setWentWrong] = useState("");

  useEffect(() => {
    listFailedTurns(threadId)
      .then((found) => {
        setTurns(found);
        setStarted(found[0]?.turn.started ?? "");
      })
      .catch(() => setFailed("The record of this conversation's turns could not be read."));
  }, [threadId]);

  // The preview is what the server will write; it trims and cleans the words again on save.
  const chosen = turns?.find((t) => t.turn.started === started);

  const save = () => {
    exportFailedTurn(threadId, { started, asked, went_wrong: wentWrong })
      .then((blob) => {
        saveBlob(blob, `failed-turn-${started.slice(0, 19).replace(/\D/g, "")}.json`);
        onClose();
      })
      .catch(() => setFailed("The file could not be made. The turn may no longer be recorded."));
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="flex max-h-[min(640px,100vh-2rem)] w-[min(560px,100vw-2rem)] flex-col gap-3 overflow-y-auto rounded-[14px] border border-[var(--border)] bg-[var(--panel-bg)] p-4 shadow-[var(--shadow)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div id={titleId} className="text-sm font-medium">
          Export a failed turn
        </div>
        <div className="text-sm text-[var(--muted)]">
          The file says how one turn went: the model, its tool calls and failures, tokens and time, and the
          start of each tool error. It holds none of the conversation's words. Nothing is sent: you save the
          file and decide who gets it, for example to turn it into a test of coscribe.
        </div>
        {failed && <div className="text-sm text-red-500">{failed}</div>}
        {turns === null && !failed && <div className="text-sm text-[var(--muted)]">Reading the record…</div>}
        {turns?.length === 0 && (
          <div className="text-sm">No failed or stopped turns are recorded for this conversation.</div>
        )}
        {turns && chosen && (
          <TurnForm
            turns={turns}
            started={started}
            onPick={setStarted}
            asked={asked}
            onAsked={setAsked}
            wentWrong={wentWrong}
            onWentWrong={setWentWrong}
            preview={JSON.stringify({ ...chosen, asked: asked.trim(), went_wrong: wentWrong.trim() }, null, 2)}
          />
        )}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--card-bg)]"
            onClick={onClose}
          >
            {turns?.length ? "Cancel" : "Close"}
          </button>
          {chosen && (
            <button
              type="button"
              className="rounded-md bg-[var(--primary)] px-3 py-1.5 text-sm text-[var(--primary-fg)] hover:bg-[var(--primary-hover)]"
              onClick={save}
            >
              Save the file
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}

/** A conversation menu's two exports: the whole conversation as Markdown, and one failed turn,
 * whose dialog the menu's owner shows once the menu has closed. */
export function ExportItems({
  thread,
  onDone,
  onFailedTurn,
}: {
  thread: ThreadSummary;
  onDone: () => void;
  onFailedTurn: () => void;
}) {
  const save = () => {
    onDone();
    exportThread(thread.thread_id)
      .then((blob) => saveBlob(blob, `conversation-${thread.thread_id.slice(0, 8)}.md`))
      .catch(() => window.alert("The conversation could not be exported."));
  };
  return (
    <>
      <button type="button" role="menuitem" className={itemClass} onClick={save}>
        <DownloadIcon className="h-3.5 w-3.5" /> Export conversation
      </button>
      <button type="button" role="menuitem" className={itemClass} onClick={onFailedTurn}>
        <DownloadIcon className="h-3.5 w-3.5" /> Export a failed turn…
      </button>
    </>
  );
}
