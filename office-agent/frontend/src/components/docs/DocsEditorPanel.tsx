import { EditorContent, useEditor } from "@tiptap/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { blocksToDoc, getDocBlocks, type DocBlocks } from "../../lib/docsEditor";
import { DocxPanelHeader } from "../DocxPanelHeader";
import { DocsToolbar } from "./DocsToolbar";
import { docsExtensions } from "../../lib/docsExtensions";
import { useDocsSave, type SaveState } from "./useDocsSave";

interface PanelProps {
  threadId: string;
  path: string;
  refreshKey: string;
  onFileChanged?: (path: string | null) => void;
  /** Back to the Word layout. */
  onPreview: () => void;
}

const SAVE_LABELS: Record<SaveState["kind"], string> = {
  saved: "Saved",
  unsaved: "Unsaved changes",
  saving: "Saving…",
  conflict: "",
  error: "",
};

/** A Word file edited in the app (decision 0019): the file read as blocks, a rich-text editor over
 * them, and each change written back to the file a moment later. */
export function DocsEditorPanel(props: PanelProps) {
  const { threadId, path, refreshKey } = props;
  const [loaded, setLoaded] = useState<{ round: number; doc: DocBlocks } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const unsaved = useRef(false);
  const load = useCallback(() => {
    setError(null);
    getDocBlocks(threadId, path).then(
      (doc) => setLoaded((now) => ({ round: (now?.round ?? 0) + 1, doc })),
      (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
    );
  }, [threadId, path]);
  // The file changed under the editor (coscribe's turn): read it again unless the person has edits waiting.
  useEffect(() => {
    if (!unsaved.current) load();
  }, [load, refreshKey]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      {loaded ? (
        <DocsEditor key={loaded.round} {...props} doc={loaded.doc} unsaved={unsaved} onReload={load} />
      ) : (
        <>
          <DocxPanelHeader threadId={threadId} path={path} onFileChanged={props.onFileChanged} />
          <div className="px-4 py-3 text-sm text-[var(--muted)]">{error ?? "Loading…"}</div>
        </>
      )}
    </div>
  );
}

function DocsEditor({ doc, unsaved, onReload, ...panel }: PanelProps & { doc: DocBlocks; unsaved: { current: boolean }; onReload: () => void }) {
  const { threadId, path } = panel;
  const editor = useEditor({
    extensions: docsExtensions,
    content: blocksToDoc(doc.blocks),
    editorProps: { attributes: { class: "docs-editor", "aria-label": "Document" } },
  });
  const { state } = useDocsSave(editor, threadId, path, doc.version, onReload);
  useEffect(() => {
    unsaved.current = state.kind !== "saved";
  }, [state, unsaved]);

  return (
    <>
      <DocxPanelHeader threadId={threadId} path={path} onFileChanged={panel.onFileChanged}>
        <span className="text-xs text-[var(--muted)]" role="status">
          {SAVE_LABELS[state.kind]}
        </span>
        <button type="button" className="flex h-7 items-center rounded-lg border border-[var(--border)] px-2.5 text-xs text-[var(--fg)] hover:bg-[var(--card-bg)]" onClick={panel.onPreview}>
          Word layout
        </button>
      </DocxPanelHeader>
      {editor && <DocsToolbar editor={editor} />}
      {(state.kind === "conflict" || state.kind === "error") && (
        <div className="flex items-center gap-3 border-b border-[var(--border)] px-4 py-2 text-xs text-[var(--danger)]">
          <span className="flex-1">
            {state.kind === "conflict" ? "This document changed since you opened it (in Word or by coscribe). Your latest edits are not saved." : state.message}
          </span>
          {state.kind === "conflict" && (
            <button type="button" className="rounded-md border border-[var(--border)] px-2 py-1 text-[var(--fg)] hover:bg-[var(--card-bg)]" onClick={onReload}>
              Reload
            </button>
          )}
        </div>
      )}
      <div className="min-h-0 flex-1 overflow-auto bg-[var(--bg)]" onClick={() => editor?.commands.focus()}>
        <div className="mx-auto max-w-[760px] px-10 pb-24 pt-8" onClick={(e) => e.stopPropagation()}>
          <EditorContent editor={editor} />
        </div>
      </div>
    </>
  );
}
