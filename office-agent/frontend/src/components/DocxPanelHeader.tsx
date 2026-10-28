import { useState, type ReactNode } from "react";
import { exportDocument, type DocsExport } from "../lib/docsExport";
import { PanelFileMenu } from "./artifacts/PanelFileMenu";
import { PanelTitleButton } from "./artifacts/PanelTitleButton";
import { useDockPanel } from "./dock/dockContext";
import { DownloadIcon } from "./icons";
import type { MenuEntry } from "./slides/SlideMenu";

const EXPORTS: { kind: DocsExport; label: string; hint: string }[] = [
  { kind: "word", label: "Export as Word", hint: ".docx" },
  { kind: "pdf", label: "Export as PDF", hint: "Print" },
  { kind: "markdown", label: "Export as Markdown", hint: ".md" },
];

/** A Word file's panel header: its name with the file menu, then what the panel adds, then the dock's controls. */
export function DocxPanelHeader({
  threadId,
  path,
  onFileChanged,
  children,
}: {
  threadId: string;
  path: string;
  onFileChanged?: (path: string | null) => void;
  children?: ReactNode;
}) {
  const dock = useDockPanel();
  const [menu, setMenu] = useState<DOMRect | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const exports: MenuEntry[] = EXPORTS.map(({ kind, label, hint }) => ({
    label,
    hint,
    icon: <DownloadIcon className="h-4 w-4" />,
    onSelect: () => {
      setProblem(null);
      exportDocument(threadId, path, kind).catch((e: unknown) => setProblem(e instanceof Error ? e.message : String(e)));
    },
  }));
  const name = path.split(/[\\/]/).pop() ?? path;
  return (
    <>
      {menu && <PanelFileMenu anchor={menu} threadId={threadId} path={path} extra={exports} onFileChanged={onFileChanged} onClose={() => setMenu(null)} />}
      <div className="flex h-12 shrink-0 items-center gap-2 px-3" {...dock.headerProps}>
        <PanelTitleButton title={name} path={path} onMenu={setMenu} />
        <div className="flex-1" />
        {problem && (
          <span className="max-w-[40%] truncate text-xs text-[var(--danger)]" role="alert" title={problem}>
            {problem}
          </span>
        )}
        {children}
        {dock.controls}
      </div>
    </>
  );
}
