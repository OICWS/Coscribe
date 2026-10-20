import { useState } from "react";
import { settleAllChanges, settleChange, type DocxChange, type DocxOperation } from "../lib/docxReview";
import { ConfirmDialog } from "./ConfirmDialog";

const textButton =
  "shrink-0 rounded-md border border-[var(--border)] px-2 py-0.5 hover:bg-[var(--card-bg)] disabled:opacity-40";

/** The bar above the page that accepts or rejects the selected tracked change, or all of them. */
export function DocxChangeBar({
  selected,
  count,
  busy,
  onAct,
}: {
  selected: DocxChange | null;
  count: number;
  busy: boolean;
  onAct: (operations: DocxOperation[]) => void;
}) {
  const [confirmAll, setConfirmAll] = useState<boolean | null>(null);
  return (
    <div className="flex h-9 shrink-0 items-center gap-2 border-b border-[var(--border)] px-3 text-xs">
      <span className="min-w-0 flex-1 truncate text-[var(--muted)]">
        {selected
          ? `${selected.kind === "insert" ? "Inserted" : "Deleted"} by ${selected.author}: ${selected.text}`
          : "Select a change to accept or reject it"}
      </span>
      {busy && <span className="text-[var(--muted)]">Applying…</span>}
      {([true, false] as const).map((accept) => (
        <button
          key={String(accept)}
          type="button"
          className={textButton}
          disabled={busy || !selected}
          onClick={() => selected && onAct(settleChange(selected.id, accept))}
        >
          {accept ? "Accept" : "Reject"}
        </button>
      ))}
      {([true, false] as const).map((accept) => (
        <button
          key={String(accept)}
          type="button"
          className={textButton}
          disabled={busy}
          onClick={() => setConfirmAll(accept)}
        >
          {accept ? "Accept all" : "Reject all"}
        </button>
      ))}
      {confirmAll !== null && (
        <ConfirmDialog
          title={confirmAll ? "Accept all changes?" : "Reject all changes?"}
          description={`This ${confirmAll ? "accepts" : "rejects"} all ${count} tracked ${count === 1 ? "change" : "changes"} and saves the file.`}
          confirmLabel={confirmAll ? "Accept all" : "Reject all"}
          tone="neutral"
          onCancel={() => setConfirmAll(null)}
          onConfirm={() => {
            onAct(settleAllChanges(confirmAll));
            setConfirmAll(null);
          }}
        />
      )}
    </div>
  );
}
