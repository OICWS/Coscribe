import { useCallback, useEffect, useRef, useState } from "react";
import type { LiveDoc } from "../../lib/docDrafts";
import { DocReading } from "./DocReading";
import { exportDoc, type DocExportKind } from "../../lib/docExport";
import { getDoc, NotADocError, restoreDoc, type DocRead } from "../../lib/docFile";
import type { CommentLink } from "../../lib/slideComments";
import { PanelFileMenu } from "../artifacts";
import { PanelTitleButton } from "../artifacts";
import { useDockPanel } from "../dock";
import { DownloadIcon } from "../icons";
import type { MenuEntry } from "../slides";
import { DocEditor } from "./DocEditor";
import { DocStepControl } from "./DocNotices";

interface PanelProps {
  threadId: string;
  path: string;
  refreshKey: string;
  draft?: LiveDoc;
  onFileChanged?: (path: string | null) => void;
  /** Sends coscribe a message; absent where there is no conversation. */
  onAsk?: (text: string, link?: CommentLink) => void;
}

/** What the person is offered after the file changed under the editor: to take that change back, to
 * do it again, or what went wrong. */
export type Step = { kind: "undo" | "redo"; to: string } | { kind: "failed"; message: string };

const message = (e: unknown) => (e instanceof Error ? e.message : String(e));

const EXPORTS: { kind: DocExportKind; label: string; hint: string }[] = [
  { kind: "word", label: "Export as Word", hint: ".docx" },
  { kind: "pdf", label: "Export as PDF", hint: "Print" },
  { kind: "markdown", label: "Export as Markdown", hint: ".md" },
];

function useDocRevisions(threadId: string, path: string, refreshKey: string, commit: string | null) {
  const [readDraft, setReadDraft] = useState<string | null>(null);

  const [loaded, setLoaded] = useState<{ round: number; doc: DocRead } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notADoc, setNotADoc] = useState(false);
  const [step, setStep] = useState<Step | null>(null);
  const unsaved = useRef(false);
  // The version the editor holds, kept up to date by its saves: a re-read that finds the same one
  // changes nothing, so the editor is not rebuilt (and its caret not lost) when nothing changed.
  const version = useRef("");
  const request = useRef(0);

  const load = useCallback(
    (force: boolean, committed: string | null = null) => {
      const reading = ++request.current;
      setError(null);
      getDoc(threadId, path).then(
        (doc) => {
          if (reading !== request.current) return;
          setNotADoc(false);
          if (committed) setReadDraft(committed);
          if (!force && (doc.version === version.current || unsaved.current)) return;
          const held = version.current;
          version.current = doc.version;
          if (held) setStep({ kind: "undo", to: held });
          setLoaded((now) => ({ round: (now?.round ?? 0) + 1, doc }));
        },
        (e: unknown) => {
          if (reading === request.current) {
            if (e instanceof NotADocError) setNotADoc(true);
            else setError(message(e));
          }
        },
      );
    },
    [threadId, path],
  );
  useEffect(() => {
    if (!unsaved.current) load(false, commit);
    return () => { request.current += 1; };
  }, [load, refreshKey, commit]);
  const reload = useCallback(() => load(true), [load]);
  const takeStep = useCallback(
    (taken: { kind: "undo" | "redo"; to: string }) => {
      const held = version.current;
      request.current += 1;
      restoreDoc(threadId, path, held, taken.to).then(
        (restored) => {
          version.current = restored.version;
          setLoaded((now) => ({ round: (now?.round ?? 0) + 1, doc: restored }));
          setStep(taken.kind === "undo" ? { kind: "redo", to: held } : null);
        },
        (e: unknown) => setStep({ kind: "failed", message: message(e) }),
      );
    },
    [threadId, path],
  );
  const dismissStep = useCallback(() => setStep(null), []);
  return { loaded, error, notADoc, step, unsaved, version, readDraft, reload, takeStep, dismissStep };
}

/** A Doc edited in the app with a stable scroll surface for saved and draft content. */
export function DocPanel(props: PanelProps) {
  const { threadId, path, draft } = props;
  const [frame, setFrame] = useState<HTMLDivElement | null>(null);
  const [scroll, setScroll] = useState<HTMLDivElement | null>(null);
  const { loaded, error, notADoc, step, unsaved, version, readDraft, reload, takeStep, dismissStep } =
    useDocRevisions(threadId, path, props.refreshKey, draft?.committed ? draft.id : null);
  const [problem, setProblem] = useState<string | null>(null);
  const [menu, setMenu] = useState<DOMRect | null>(null);
  const dock = useDockPanel();

  const exports: MenuEntry[] = EXPORTS.map(({ kind, label, hint }) => ({
    label,
    hint,
    icon: <DownloadIcon className="h-4 w-4" />,
    onSelect: () => {
      setProblem(null);
      exportDoc(threadId, path, kind).catch((e: unknown) => setProblem(message(e)));
    },
  }));
  const visibleDraft = draft && readDraft !== draft.id && !unsaved.current ? draft : undefined;
  const name = path.split(/[\\/]/).pop() ?? path;
  return (
    <div className="flex h-full min-h-0 flex-col">
      {menu && <PanelFileMenu anchor={menu} threadId={threadId} path={path} extra={notADoc ? undefined : exports} onFileChanged={props.onFileChanged} onClose={() => setMenu(null)} />}
      <div className="flex h-12 shrink-0 items-center gap-2 px-3" {...dock.headerProps}>
        <PanelTitleButton title={name} path={path} onMenu={setMenu} />
        <div className="flex-1" />
        {problem && (
          <span className="max-w-[40%] truncate text-xs text-[var(--danger)]" role="alert" title={problem}>
            {problem}
          </span>
        )}
        {step && <DocStepControl step={step} onStep={takeStep} onDismiss={dismissStep} />}
        <span id="doc-comments-toggle" />
        <span id="doc-save-state" className="text-xs text-[var(--muted)]" role="status" />
        {dock.controls}
      </div>
      {loaded ? (
        <DocEditor key={loaded.round} {...props} scroll={scroll} frame={frame} previewing={!!visibleDraft} doc={loaded.doc} unsaved={unsaved} version={version} onReload={reload} onDismissStep={dismissStep} />
      ) : !visibleDraft && (
        <div className="px-4 py-3 text-sm text-[var(--muted)]">{notADoc ? "This Markdown file is not a Doc. Use the menu under its name to open it in your default app." : (error ?? "Loading…")}</div>
      )}
      <div ref={setFrame} className="relative min-h-0 flex-1">
        <div ref={setScroll} data-doc-scroll className="h-full overflow-auto bg-[var(--bg)] [overflow-anchor:none]">
          {visibleDraft && <DocReading threadId={threadId} path={path} blocks={visibleDraft.blocks} />}
        </div>
      </div>
    </div>
  );
}
