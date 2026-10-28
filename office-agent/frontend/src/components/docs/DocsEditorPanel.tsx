import { useEditor } from "@tiptap/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { askAboutWords, blocksToDoc, docImageUrl, getDocBlocks, restoreDocVersion, type Block, type DocBlocks } from "../../lib/docsEditor";
import { DocxPanelHeader } from "../DocxPanelHeader";
import { DocsBubble } from "./DocsBubble";
import { PictureBar } from "./PictureBar";
import { DocsToolbar } from "./DocsToolbar";
import { SlashMenu, useSlashMenu } from "./SlashMenu";
import { docsExtensions } from "../../lib/docsExtensions";
import { PROBLEM_EVENT } from "../../lib/docsPictures";
import { baseStyle } from "../../lib/docsLook";
import { DocsSheet } from "./DocsSheet";
import { useDocsSave, type SaveState } from "./useDocsSave";

interface PanelProps {
  threadId: string;
  path: string;
  refreshKey: string;
  onFileChanged?: (path: string | null) => void;
  /** Sends coscribe a message about selected words; absent where there is no conversation. */
  onAsk?: (text: string) => void;
}

/** What the person is offered after the file changed under the editor: to take that change back, to
 * do it again, or what went wrong. */
export type Step = { kind: "undo" | "redo"; to: string } | { kind: "failed"; message: string };

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
  const [step, setStep] = useState<Step | null>(null);
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
        const held = version.current;
        version.current = doc.version;
        if (held) setStep({ kind: "undo", to: held });
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
  const takeStep = useCallback(
    (taken: { kind: "undo" | "redo"; to: string }) => {
      const held = version.current;
      restoreDocVersion(threadId, path, held, taken.to).then(
        (restored) => {
          version.current = restored.version;
          setLoaded((now) => ({ round: (now?.round ?? 0) + 1, doc: restored }));
          setStep(taken.kind === "undo" ? { kind: "redo", to: held } : null);
        },
        (e: unknown) => setStep({ kind: "failed", message: e instanceof Error ? e.message : String(e) }),
      );
    },
    [threadId, path],
  );
  const dismissStep = useCallback(() => setStep(null), []);

  return (
    <div className="flex h-full min-h-0 flex-col">
      {loaded ? (
        <DocsEditor key={loaded.round} {...props} doc={loaded.doc} unsaved={unsaved} version={version} onReload={reload} step={step} onStep={takeStep} onDismissStep={dismissStep} />
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
  step,
  onStep,
  onDismissStep,
  ...panel
}: PanelProps & {
  doc: DocBlocks;
  unsaved: { current: boolean };
  version: { current: string };
  onReload: () => void;
  step: Step | null;
  onStep: (taken: { kind: "undo" | "redo"; to: string }) => void;
  onDismissStep: () => void;
}) {
  const { threadId, path } = panel;
  const slash = useSlashMenu();
  const editor = useEditor({
    extensions: [...docsExtensions, slash.extension],
    content: blocksToDoc(doc.blocks, docImageUrl(threadId, path, doc.version)),
    editorProps: { attributes: { class: doc.page ? "docs-editor word-look" : "docs-editor", "aria-label": "Document", ...(doc.page ? { style: baseStyle(doc.page) } : {}) } },
  });
  const toContent = useCallback((blocks: Block[], at: string) => blocksToDoc(blocks, docImageUrl(threadId, path, at)), [threadId, path]);
  const { state } = useDocsSave(editor, threadId, path, version, doc.blocks, toContent, onReload);
  const [notice, setNotice] = useState<string | null>(null);
  const page = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = page.current;
    const show = (event: Event) => setNotice(String((event as CustomEvent).detail));
    element?.addEventListener(PROBLEM_EVENT, show);
    return () => element?.removeEventListener(PROBLEM_EVENT, show);
  }, []);
  useEffect(() => {
    unsaved.current = state.kind !== "saved";
    // Typing after the change ends the offer: taking it back would take the typing back with it.
    if (state.kind === "unsaved" || state.kind === "saving") onDismissStep();
  }, [state, unsaved, onDismissStep]);

  return (
    <>
      <DocxPanelHeader threadId={threadId} path={path} onFileChanged={panel.onFileChanged}>
        <span className="text-xs text-[var(--muted)]" role="status">
          {SAVE_LABELS[state.kind]}
        </span>
      </DocxPanelHeader>
      {editor && <DocsToolbar editor={editor} />}
      {editor && <PictureBar editor={editor} />}
      {editor && <DocsBubble editor={editor} onAsk={panel.onAsk && ((instruction, words) => panel.onAsk?.(`${askAboutWords(path, words)}\n\n${instruction}`))} />}
      {(state.kind === "conflict" || state.kind === "error") && (
        <div className="flex items-center gap-3 border-b border-[var(--border)] px-4 py-2 text-xs text-[var(--danger)]">
          <span className="flex-1">
            {state.kind === "conflict" ? "This document changed since you opened it (in Word or by Coscribe). Your latest edits are not saved." : state.message}
          </span>
          {state.kind === "conflict" && (
            <button type="button" className="rounded-md border border-[var(--border)] px-2 py-1 text-[var(--fg)] hover:bg-[var(--card-bg)]" onClick={onReload}>
              Reload
            </button>
          )}
        </div>
      )}
      {step && (
        <div className="flex items-center gap-3 border-b border-[var(--border)] px-4 py-2 text-xs text-[var(--muted)]" role="group" aria-label="Change to this document">
          <span className="flex-1">
            {step.kind === "undo" && "This document was changed by Coscribe or another program."}
            {step.kind === "redo" && "The earlier version is back."}
            {step.kind === "failed" && step.message}
          </span>
          {step.kind !== "failed" && (
            <button type="button" className="rounded-md border border-[var(--border)] px-2 py-1 text-[var(--fg)] hover:bg-[var(--card-bg)]" onClick={() => onStep(step)}>
              {step.kind === "undo" ? "Undo" : "Redo"}
            </button>
          )}
          <button type="button" className="rounded-md px-2 py-1 hover:bg-[var(--card-bg)]" onClick={onDismissStep}>
            Dismiss
          </button>
        </div>
      )}
      {notice && (
        <div className="flex items-center gap-3 border-b border-[var(--border)] px-4 py-2 text-xs text-[var(--danger)]" role="alert">
          <span className="flex-1">{notice}</span>
          <button type="button" className="rounded-md border border-[var(--border)] px-2 py-1 text-[var(--fg)] hover:bg-[var(--card-bg)]" onClick={() => setNotice(null)}>
            Dismiss
          </button>
        </div>
      )}
      <DocsSheet editor={editor} page={doc.page} pageRef={page} />
      {slash.open && <SlashMenu open={slash.open} selected={slash.selected} onHover={slash.setSelected} />}
    </>
  );
}
