import { useCallback, useEffect, useRef, useState } from "react";
import { getDoc, restoreDoc, type DocRead } from "../../lib/docFile";
import { PanelFileMenu } from "../artifacts/PanelFileMenu";
import { PanelTitleButton } from "../artifacts/PanelTitleButton";
import { useDockPanel } from "../dock/dockContext";
import { DocEditor } from "./DocEditor";

interface PanelProps {
  threadId: string;
  path: string;
  refreshKey: string;
  onFileChanged?: (path: string | null) => void;
  /** Sends coscribe a message; absent where there is no conversation. */
  onAsk?: (text: string) => void;
}

/** What the person is offered after the file changed under the editor: to take that change back, to
 * do it again, or what went wrong. */
export type Step = { kind: "undo" | "redo"; to: string } | { kind: "failed"; message: string };

const message = (e: unknown) => (e instanceof Error ? e.message : String(e));

/** A Doc edited in the app (decision 0025): the file read as blocks, a rich-text editor over them, and
 * each change written back as edits to the blocks it touched. */
export function DocPanel(props: PanelProps) {
  const { threadId, path, refreshKey } = props;
  const [loaded, setLoaded] = useState<{ round: number; doc: DocRead } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<Step | null>(null);
  const [menu, setMenu] = useState<DOMRect | null>(null);
  const unsaved = useRef(false);
  // The version the editor holds, kept up to date by its saves: a re-read that finds the same one
  // changes nothing, so the editor is not rebuilt (and its caret not lost) when nothing changed.
  const version = useRef("");
  const dock = useDockPanel();

  const load = useCallback(
    (force: boolean) => {
      setError(null);
      getDoc(threadId, path).then(
        (doc) => {
          if (!force && (doc.version === version.current || unsaved.current)) return;
          const held = version.current;
          version.current = doc.version;
          if (held) setStep({ kind: "undo", to: held });
          setLoaded((now) => ({ round: (now?.round ?? 0) + 1, doc }));
        },
        (e: unknown) => setError(message(e)),
      );
    },
    [threadId, path],
  );
  useEffect(() => {
    if (!unsaved.current) load(false);
  }, [load, refreshKey]);
  const reload = useCallback(() => load(true), [load]);
  const takeStep = useCallback(
    (taken: { kind: "undo" | "redo"; to: string }) => {
      const held = version.current;
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

  const name = path.split(/[\\/]/).pop() ?? path;
  return (
    <div className="flex h-full min-h-0 flex-col">
      {menu && <PanelFileMenu anchor={menu} threadId={threadId} path={path} onFileChanged={props.onFileChanged} onClose={() => setMenu(null)} />}
      <div className="flex h-12 shrink-0 items-center gap-2 px-3" {...dock.headerProps}>
        <PanelTitleButton title={name} path={path} onMenu={setMenu} />
        <div className="flex-1" />
        <span id="doc-save-state" className="text-xs text-[var(--muted)]" role="status" />
        {dock.controls}
      </div>
      {loaded ? (
        <DocEditor key={loaded.round} {...props} doc={loaded.doc} unsaved={unsaved} version={version} onReload={reload} step={step} onStep={takeStep} onDismissStep={dismissStep} />
      ) : (
        <div className="px-4 py-3 text-sm text-[var(--muted)]">{error ?? "Loading…"}</div>
      )}
    </div>
  );
}
