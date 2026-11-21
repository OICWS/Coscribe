import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { DIALOG_BACKDROP_CLASS } from "../../lib/titleBar";
import { CloseIcon } from "../icons";
import { primaryButtonClass } from "./SettingRow";

/** A setting managed in a dialog of its own, laid out like the workspace dialog: a header, a body
 * that scrolls in a short window, and Done in the footer. Each change inside applies at once, so
 * there is nothing to cancel. */
export function SettingsDialog({ title, description, onClose, children }: { title: string; description?: ReactNode; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return createPortal(
    <div className={DIALOG_BACKDROP_CLASS} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="flex max-h-full w-full max-w-[42.5rem] flex-col overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--panel-bg)] shadow-[var(--shadow)]"
      >
        <div className="flex items-start gap-2 px-6 pb-3 pt-5">
          <div className="min-w-0 flex-1">
            <h2 className="text-xl font-semibold leading-tight">{title}</h2>
            {description && <p className="mt-1 text-sm leading-relaxed text-[var(--muted)]">{description}</p>}
          </div>
          <button
            type="button"
            aria-label="Close"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
            onClick={onClose}
          >
            <CloseIcon className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-5 pt-1">{children}</div>
        <div className="flex justify-end border-t border-[var(--border)] px-6 py-4">
          <button type="button" className={primaryButtonClass} onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
