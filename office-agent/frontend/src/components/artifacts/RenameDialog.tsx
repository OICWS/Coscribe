import { useState } from "react";
import { createPortal } from "react-dom";

/** A new name, asked in the app's own dialog; `rename` makes the change and what it returns goes to `onDone`. */
export function RenameDialog<T>({ current, rename, onCancel, onDone }: { current: string; rename: (name: string) => Promise<T>; onCancel: () => void; onDone: (result: T) => void }) {
  const [name, setName] = useState(current);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = () => {
    if (!name.trim() || busy) return;
    setBusy(true);
    rename(name).then(onDone, (e: unknown) => {
      setBusy(false);
      setError(e instanceof Error ? e.message : String(e));
    });
  };
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onCancel}>
      <form
        className="w-[min(380px,100vw-2rem)] rounded-[14px] border border-[var(--border)] bg-[var(--panel-bg)] p-4 shadow-[var(--shadow)]"
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <div className="mb-3 text-sm font-medium">Rename</div>
        <input
          autoFocus
          aria-label="Name"
          value={name}
          maxLength={200}
          className="h-9 w-full rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-3 text-sm outline-none focus:border-[var(--focus)]"
          onFocus={(e) => e.currentTarget.select()}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Escape" && onCancel()}
        />
        {error && <div className="mt-2 text-sm text-[var(--danger)]">{error}</div>}
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--card-bg)]" onClick={onCancel}>
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim() || busy}
            className="rounded-md bg-[var(--primary)] px-3 py-1.5 text-sm text-[var(--primary-fg)] hover:bg-[var(--primary-hover)] disabled:opacity-50"
          >
            Rename
          </button>
        </div>
      </form>
    </div>,
    document.body,
  );
}
