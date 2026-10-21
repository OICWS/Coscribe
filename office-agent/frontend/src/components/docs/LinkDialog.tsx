import type { Editor } from "@tiptap/core";
import { useState } from "react";
import { createPortal } from "react-dom";

const LINK_START = /^(https?:\/\/|mailto:)/i;

/** The address of the selected words' link, asked in the app's own dialog. */
export function LinkDialog({ editor, onClose }: { editor: Editor; onClose: () => void }) {
  const [address, setAddress] = useState<string>((editor.getAttributes("link").href as string | undefined) ?? "");
  const apply = () => {
    const wanted = address.trim();
    if (!wanted) editor.chain().focus().extendMarkRange("link").unsetLink().run();
    else editor.chain().focus().extendMarkRange("link").setLink({ href: LINK_START.test(wanted) ? wanted : `https://${wanted}` }).run();
    onClose();
  };
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <form
        className="w-[min(420px,100vw-2rem)] rounded-[14px] border border-[var(--border)] bg-[var(--panel-bg)] p-4 shadow-[var(--shadow)]"
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          apply();
        }}
      >
        <div className="mb-3 text-sm font-medium">Link</div>
        <input
          autoFocus
          aria-label="Address"
          placeholder="https://"
          value={address}
          className="h-9 w-full rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-3 text-sm outline-none focus:border-[var(--focus)]"
          onChange={(e) => setAddress(e.target.value)}
          onKeyDown={(e) => e.key === "Escape" && onClose()}
        />
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--card-bg)]" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="rounded-md bg-[var(--primary)] px-3 py-1.5 text-sm text-[var(--primary-fg)] hover:bg-[var(--primary-hover)]">
            {address.trim() ? "Apply" : "Remove link"}
          </button>
        </div>
      </form>
    </div>,
    document.body,
  );
}
