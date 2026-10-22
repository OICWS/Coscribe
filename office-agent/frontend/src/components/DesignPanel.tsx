import { useState, type ReactNode } from "react";
import { designFileUrl } from "../lib/artifacts";
import { exportDesign, type DesignExport } from "../lib/designExport";
import { PanelFileMenu } from "./artifacts/PanelFileMenu";
import { PanelTitleButton } from "./artifacts/PanelTitleButton";
import { useDockPanel } from "./dock/dockContext";
import { CodeIcon, DownloadIcon } from "./icons";
import type { MenuEntry } from "./slides/SlideMenu";

const EXPORTS: { kind: DesignExport; label: string; description: string; icon: ReactNode; download: boolean }[] = [
  { kind: "html", label: "HTML", description: "Standalone web page", icon: <CodeIcon className="h-5 w-5" />, download: true },
  { kind: "pdf", label: "PDF", description: "Opens your browser\u2019s print dialog", icon: <span className="text-[10px] font-bold text-[var(--file-pdf)]">PDF</span>, download: false },
];

/** A design page coscribe made, beside the conversation: the HTML file drawn in a sandboxed frame
 * (no network, no access to the app) and drawn again whenever the file is written. */
export function DesignPanel({
  threadId,
  path,
  refreshKey,
  onFileChanged,
}: {
  threadId: string;
  path: string;
  refreshKey: string;
  /** The file was renamed (its new path) or deleted (null) from its menu. */
  onFileChanged?: (path: string | null) => void;
}) {
  const dock = useDockPanel();
  const [menu, setMenu] = useState<DOMRect | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const exports: MenuEntry[] = [
    {
      label: "Export",
      icon: <DownloadIcon className="h-4 w-4" />,
      submenu: EXPORTS.map(({ kind, label, description, icon, download }) => ({
        label,
        description,
        icon: <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--bg)]">{icon}</span>,
        trailing: download ? <DownloadIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" /> : undefined,
        onSelect: () => {
          setProblem(null);
          exportDesign(threadId, path, refreshKey, kind).catch((e: unknown) => setProblem(e instanceof Error ? e.message : String(e)));
        },
      })),
    },
  ];
  const name = path.split(/[\\/]/).pop() ?? path;
  return (
    <div className="flex h-full min-h-0 flex-col">
      {menu && <PanelFileMenu anchor={menu} threadId={threadId} path={path} extra={exports} onFileChanged={onFileChanged} onClose={() => setMenu(null)} />}
      <div className="flex h-12 shrink-0 items-center gap-2 px-3" {...dock.headerProps}>
        <PanelTitleButton title={name} path={path} onMenu={setMenu} />
        <div className="flex-1" />
        {problem && (
          <span className="max-w-[40%] truncate text-xs text-[var(--danger)]" role="alert" title={problem}>
            {problem}
          </span>
        )}
        {dock.controls}
      </div>
      <iframe
        key={`${path}.${refreshKey}`}
        title={name}
        src={designFileUrl(threadId, path, refreshKey)}
        sandbox="allow-scripts"
        className="min-h-0 w-full flex-1 border-0 bg-white"
      />
    </div>
  );
}
