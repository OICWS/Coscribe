import { EditorContent, useEditor } from "@tiptap/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import type { DocRead } from "../../lib/docFile";
import { loadLook, saveLook, type DocLook } from "../../lib/docLook";
import { DocChartPreview } from "../../lib/docChartPreview";
import { docContent, docExtensions, loadedOf } from "../../lib/docModel";
import { askAboutWords } from "../../lib/docsEditor";
import type { Step } from "./DocPanel";
import { DocBubble } from "./DocBubble";
import { DocToolbar } from "./DocToolbar";
import { useDocSave, type SaveState } from "./useDocSave";

const SAVE_LABELS: Record<SaveState["kind"], string> = { saved: "Saved", unsaved: "Unsaved changes", saving: "Saving…", conflict: "", error: "" };

const bar = "flex items-center gap-3 border-b border-[var(--border)] px-4 py-2 text-xs";
const small = "rounded-md border border-[var(--border)] px-2 py-1 text-[var(--fg)] hover:bg-[var(--card-bg)]";

export function DocEditor({
  threadId,
  path,
  doc,
  unsaved,
  version,
  onReload,
  step,
  onStep,
  onDismissStep,
  onAsk,
}: {
  threadId: string;
  path: string;
  doc: DocRead;
  unsaved: { current: boolean };
  version: { current: string };
  onReload: () => void;
  step: Step | null;
  onStep: (taken: { kind: "undo" | "redo"; to: string }) => void;
  onDismissStep: () => void;
  onAsk?: (text: string) => void;
}) {
  const [look, setLook] = useState<DocLook>(loadLook);
  const changeLook = useCallback((next: DocLook) => {
    setLook(next);
    saveLook(next);
  }, []);
  const content = useMemo(() => docContent(doc.blocks), [doc]);
  const editor = useEditor({
    extensions: [...docExtensions, DocChartPreview],
    content,
    editorProps: { attributes: { class: "doc-editor", "aria-label": "Document" } },
  });
  const initial = useMemo(() => (editor ? loadedOf(editor.state.doc, doc.blocks) : new Map()), [editor, doc]);
  const { state } = useDocSave(editor, threadId, path, version, initial, onReload);
  useEffect(() => {
    unsaved.current = state.kind !== "saved";
    // Typing after the change ends the offer: taking it back would take the typing back with it.
    if (state.kind === "unsaved" || state.kind === "saving") onDismissStep();
  }, [state, unsaved, onDismissStep]);
  const [slot, setSlot] = useState<HTMLElement | null>(null);
  useEffect(() => setSlot(document.getElementById("doc-save-state")), []);

  return (
    <>
      {slot && createPortal(SAVE_LABELS[state.kind], slot)}
      {editor && <DocToolbar editor={editor} look={look} onLook={changeLook} />}
      {editor && <DocBubble editor={editor} onAsk={onAsk && ((instruction, words) => onAsk(`${askAboutWords(path, words)}\n\n${instruction}`))} />}
      {(state.kind === "conflict" || state.kind === "error") && (
        <div className={`${bar} text-[var(--danger)]`}>
          <span className="flex-1">{state.kind === "conflict" ? "This document changed since you opened it. Your latest edits are not saved." : state.message}</span>
          {state.kind === "conflict" && (
            <button type="button" className={small} onClick={onReload}>
              Reload
            </button>
          )}
        </div>
      )}
      {step && (
        <div className={`${bar} text-[var(--muted)]`} role="group" aria-label="Change to this document">
          <span className="flex-1">
            {step.kind === "undo" && "This document was changed by Coscribe or another program."}
            {step.kind === "redo" && "The earlier version is back."}
            {step.kind === "failed" && step.message}
          </span>
          {step.kind !== "failed" && (
            <button type="button" className={small} onClick={() => onStep(step)}>
              {step.kind === "undo" ? "Undo" : "Redo"}
            </button>
          )}
          <button type="button" className="rounded-md px-2 py-1 hover:bg-[var(--card-bg)]" onClick={onDismissStep}>
            Dismiss
          </button>
        </div>
      )}
      <div className="min-h-0 flex-1 overflow-auto bg-[var(--bg)]" onClick={() => editor?.commands.focus()}>
        <div
          className={`doc-page mx-auto px-10 pb-24 pt-8 ${look.wide ? "max-w-[1100px]" : "max-w-[760px]"}`}
          data-headings={look.headings}
          data-text={look.text}
          onClick={(e) => e.stopPropagation()}
        >
          <EditorContent editor={editor} />
        </div>
      </div>
    </>
  );
}
