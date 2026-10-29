import { EditorContent, useEditor } from "@tiptap/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { DocCommentMarks } from "../../lib/docCommentMarks";
import { askAboutWords, deleteDocComment, editDocComment, replyToDocComment, resolveDocComment } from "../../lib/docComments";
import type { DocRead } from "../../lib/docFile";
import { loadLook, saveLook, type DocLook } from "../../lib/docLook";
import { DocChartPreview } from "../../lib/docChartPreview";
import { DocTableLook } from "../../lib/docTableLook";
import { docContent, editorExtensions, loadedOf } from "../../lib/docModel";
import { DocPictureDrop, choosePicture, pictureUrl } from "../../lib/docPictures";
import type { CommentLink } from "../../lib/slideComments";
import { DocBubble } from "./DocBubble";
import { CommentsPopover, CommentsToggle } from "./DocComments";
import { DocNotices } from "./DocNotices";
import type { Step } from "./DocPanel";
import { DocToolbar } from "./DocToolbar";
import { useDocCommentFlow } from "./useDocCommentFlow";
import { useAddPicture } from "./useAddPicture";
import { useDocSave, type SaveState } from "./useDocSave";

const SAVE_LABELS: Record<SaveState["kind"], string> = {
  saved: "Saved",
  unsaved: "Unsaved changes",
  saving: "Saving…",
  conflict: "",
  error: "",
};

export function DocEditor({
  threadId,
  path,
  refreshKey,
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
  refreshKey: string;
  doc: DocRead;
  unsaved: { current: boolean };
  version: { current: string };
  onReload: () => void;
  step: Step | null;
  onStep: (taken: { kind: "undo" | "redo"; to: string }) => void;
  onDismissStep: () => void;
  onAsk?: (text: string, link?: CommentLink) => void;
}) {
  const [look, setLook] = useState<DocLook>(loadLook);
  const changeLook = useCallback((next: DocLook) => {
    setLook(next);
    saveLook(next);
  }, []);
  const content = useMemo(() => docContent(doc.blocks), [doc]);
  const addPicture = useRef<(file: File) => void>(() => undefined);
  const extensions = useMemo(
    () => [...editorExtensions((src) => pictureUrl(threadId, path, src)), DocCommentMarks, DocChartPreview, DocTableLook, DocPictureDrop.configure({ onFile: (file) => addPicture.current(file) })],
    [threadId, path],
  );
  const editor = useEditor({
    extensions,
    content,
    editorProps: { attributes: { class: "doc-editor", "aria-label": "Document" } },
  });
  const initial = useMemo(() => (editor ? loadedOf(editor.state.doc, doc.blocks) : new Map()), [editor, doc]);
  const { state, loaded, flush } = useDocSave(editor, threadId, path, version, initial, onReload);
  const comments = useDocCommentFlow({ editor, threadId, path, refreshKey, saveState: state.kind, loaded, flush, onAsk });
  const { store } = comments;
  useAddPicture(addPicture, editor, threadId, path, comments.setProblem);
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
      <CommentsToggle shown={comments.show} dot={comments.open.length > 0} onToggle={() => comments.setShow((now) => !now)} />
      {editor && <DocToolbar editor={editor} look={look} onLook={changeLook} onPicture={() => choosePicture((file) => addPicture.current(file))} />}
      {editor && (
        <DocBubble editor={editor} onAsk={onAsk && ((instruction, words) => onAsk(`${askAboutWords(path, words)}\n\n${instruction}`))} onComment={(text, send) => void comments.add(text, send)} />
      )}
      <DocNotices
        problem={comments.problem ?? store.failed}
        onDismissProblem={() => comments.setProblem(null)}
        state={state}
        onReload={onReload}
        step={step}
        onStep={onStep}
        onDismissStep={onDismissStep}
      />
      <div className="relative min-h-0 flex-1">
        {comments.show && (
          <CommentsPopover
            comments={store.comments}
            focus={comments.focus}
            hintFor={comments.hintFor}
            onSendUnsent={onAsk && comments.sendUnsent}
            onResolve={(id, resolved) => void store.act(resolveDocComment(threadId, path, id, resolved))}
            onReply={(id, text) => void store.act(replyToDocComment(threadId, path, id, text))}
            onEdit={(id, text) => void store.act(editDocComment(threadId, path, id, text))}
            onDelete={(id) => void store.act(deleteDocComment(threadId, path, id))}
            onClose={() => comments.setShow(false)}
          />
        )}
        <div data-doc-scroll className="h-full overflow-auto bg-[var(--bg)]" onClick={() => editor?.commands.focus()}>
          <div
            className={`doc-page mx-auto px-10 pb-24 pt-8 ${look.wide ? "max-w-[1100px]" : "max-w-[760px]"}`}
            data-headings={look.headings}
            data-text={look.text}
            onClick={(e) => e.stopPropagation()}
          >
            <EditorContent editor={editor} />
          </div>
        </div>
      </div>
    </>
  );
}
