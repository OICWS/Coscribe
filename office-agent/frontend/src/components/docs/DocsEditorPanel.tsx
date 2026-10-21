import { EditorContent, useEditor } from "@tiptap/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { askAboutWords, blocksToDoc, docImageUrl, getDocBlocks, type DocBlocks } from "../../lib/docsEditor";
import { DocxPanelHeader } from "../DocxPanelHeader";
import { DocsBubble } from "./DocsBubble";
import { DocsToolbar } from "./DocsToolbar";
import { SlashMenu, useSlashMenu } from "./SlashMenu";
import { docsExtensions } from "../../lib/docsExtensions";
import { useDocsSave, type SaveState } from "./useDocsSave";

interface PanelProps {
  threadId: string;
  path: string;
  refreshKey: string;
  onFileChanged?: (path: string | null) => void;
  /** Sends coscribe a message about selected words; absent where there is no conversation. */
  onAsk?: (text: string) => void;
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
  // The version of the file the editor holds, kept up to date by its saves: a re-read that finds the
  // same one changes nothing, so the editor is not rebuilt (and its caret not lost) when nothing changed.
  const version = useRef("");
  const load = useCallback((force: boolean) => {
    setError(null);
    getDocBlocks(threadId, path).then(
      (doc) => {
        // A background read never replaces edits waiting to be saved, and finding the same version it
        // changes nothing; the person's own Reload (and a save that lost the blocks) takes the file as it is.
        if (!force && (doc.version === version.current || unsaved.current)) return;
        // Set here, not once the editor mounts: two reads in flight together must not both build one.
        version.current = doc.version;
        setLoaded((now) => ({ round: (now?.round ?? 0) + 1, doc }));
      },
      (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
    );
  }, [threadId, path]);
  // The file changed under the editor (coscribe's turn): read it again unless the person has edits waiting.
  useEffect(() => {
    if (!unsaved.current) load(false);
  }, [load, refreshKey]);
  const reload = useCallback(() => load(true), [load]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      {loaded ? (
        <DocsEditor key={loaded.round} {...props} doc={loaded.doc} unsaved={unsaved} version={version} onReload={reload} />
      ) : (
        <>
          <DocxPanelHeader threadId={threadId} path={path} onFileChanged={props.onFileChanged} />
          <div className="px-4 py-3 text-sm text-[var(--muted)]">{error ?? "Loading…"}</div>
        </>
      )}
    </div>
  );
}

function DocsEditor({
  doc,
  unsaved,
  version,
  onReload,
  ...panel
}: PanelProps & { doc: DocBlocks; unsaved: { current: boolean }; version: { current: string }; onReload: () => void }) {
  const { threadId, path } = panel;
  const slash = useSlashMenu();
  const editor = useEditor({
    extensions: [...docsExtensions, slash.extension],
    content: blocksToDoc(doc.blocks, docImageUrl(threadId, path, doc.version)),
    editorProps: { attributes: { class: "docs-editor", "aria-label": "Document" } },
  });
  const { state } = useDocsSave(editor, threadId, path, version, onReload);
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
      {editor && <DocsBubble editor={editor} onAsk={panel.onAsk && ((words) => panel.onAsk?.(askAboutWords(path, words)))} />}
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
      {slash.open && <SlashMenu open={slash.open} selected={slash.selected} onHover={slash.setSelected} />}
    </>
  );
}
