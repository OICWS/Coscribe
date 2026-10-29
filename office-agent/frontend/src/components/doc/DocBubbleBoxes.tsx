import { useState } from "react";
import { ArrowUpIcon } from "../icons";

const QUICK = ["Make it shorter", "Make it simpler", "Fix spelling and grammar"];

/** What coscribe is asked about the selected words: they are quoted, then what to do with them. */
export function AskBox({ onAsk, onClose }: { onAsk: (instruction: string) => void; onClose: () => void }) {
  const [text, setText] = useState("");
  const send = (instruction: string) => {
    if (!instruction.trim()) return;
    onAsk(instruction.trim());
    onClose();
  };
  return (
    <div className="w-[min(480px,90vw)] rounded-xl border border-[var(--border)] bg-[var(--bg)] px-3 pb-3 pt-2 shadow-[0_8px_28px_rgba(0,0,0,0.12)]" onMouseDown={(e) => e.stopPropagation()}>
      <div className="flex items-center gap-2">
        <span className="shrink-0 rounded-md bg-[color-mix(in_srgb,var(--accent)_14%,transparent)] px-1.5 py-0.5 text-sm text-[var(--accent)]">@Coscribe</span>
        <input
          autoFocus
          aria-label="Tell coscribe what to change"
          placeholder="Tell coscribe what to change"
          value={text}
          className="h-9 min-w-0 flex-1 bg-transparent text-sm outline-none"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send(text);
            if (e.key === "Escape") onClose();
          }}
        />
      </div>
      <div className="flex justify-end">
        <button type="button" aria-label="Send" title="Send" disabled={!text.trim()} className="rounded-md p-1 text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)] disabled:opacity-40 disabled:hover:bg-transparent" onClick={() => send(text)}>
          <ArrowUpIcon className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {QUICK.map((label) => (
          <button key={label} type="button" className="whitespace-nowrap rounded-lg border border-[var(--border)] px-2.5 py-1 text-sm hover:bg-[var(--card-bg)]" onClick={() => send(label)}>
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

/** A comment on the selected words: its text, and whether it goes to coscribe now or waits to be sent with others. */
export function Composer({ canSend, onComment, onClose }: { canSend: boolean; onComment: (text: string, send: boolean) => void; onClose: () => void }) {
  const [text, setText] = useState("");
  const [send, setSend] = useState(false);
  const submit = () => {
    if (!text.trim()) return;
    onComment(text.trim(), send && canSend);
    onClose();
  };
  return (
    <div className="w-[min(340px,90vw)] rounded-xl border border-[var(--border)] bg-[var(--bg)] p-3 shadow-[0_8px_28px_rgba(0,0,0,0.12)]" onMouseDown={(e) => e.stopPropagation()}>
      <textarea
        autoFocus
        aria-label="Comment"
        placeholder="Add a comment"
        rows={3}
        value={text}
        className="w-full resize-none bg-transparent text-sm outline-none"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
          if (e.key === "Escape") onClose();
        }}
      />
      <div className="mt-2 flex items-center gap-2">
        {canSend && (
          <label className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
            <input type="checkbox" checked={send} onChange={(e) => setSend(e.target.checked)} />
            Send to coscribe
          </label>
        )}
        <div className="flex-1" />
        <button type="button" className="rounded-md px-2 py-1 text-xs hover:bg-[var(--card-bg)]" onClick={onClose}>
          Cancel
        </button>
        <button
          type="button"
          disabled={!text.trim()}
          className="rounded-md bg-[var(--primary)] px-2.5 py-1 text-xs text-[var(--primary-fg)] hover:bg-[var(--primary-hover)] disabled:opacity-40"
          onClick={submit}
        >
          Comment
        </button>
      </div>
    </div>
  );
}
