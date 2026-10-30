import { useEffect, useState, type ReactNode } from "react";
import { dashboardInfo, designFileUrl, type DashboardInfo } from "../lib/artifacts";
import { exportDesign, type DesignExport } from "../lib/designExport";
import { PanelFileMenu } from "./artifacts/PanelFileMenu";
import { PanelTitleButton } from "./artifacts/PanelTitleButton";
import { useDockPanel } from "./dock/dockContext";
import { CodeIcon, DownloadIcon, ReloadIcon } from "./icons";
import type { MenuEntry } from "./slides/SlideMenu";

const EXPORTS: { kind: DesignExport; label: string; description: string; icon: ReactNode; download: boolean }[] = [
  { kind: "html", label: "HTML", description: "Standalone web page", icon: <CodeIcon className="h-5 w-5" />, download: true },
  { kind: "pdf", label: "PDF", description: "Opens your browser\u2019s print dialog", icon: <span className="text-[10px] font-bold text-[var(--file-pdf)]">PDF</span>, download: false },
];

/** When a dashboard's data was made: the oldest of its datasets, so a stale one is not hidden. */
function dataTime(info: DashboardInfo): string | null {
  const times = info.datasets.map((d) => d.updated).filter((t): t is string => !!t).sort();
  if (!times.length) return null;
  const at = new Date(times[0]);
  return Number.isNaN(at.getTime()) ? times[0] : at.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/** A design page or a dashboard coscribe made, beside the conversation: the HTML file drawn in a
 * sandboxed frame (no network, no access to the app) and drawn again whenever a turn writes a file.
 * A dashboard also says when its data was made and offers to refresh it. */
export function DesignPanel({
  threadId,
  path,
  refreshKey,
  onFileChanged,
  onSend,
  busy = false,
}: {
  threadId: string;
  path: string;
  refreshKey: string;
  /** The file was renamed (its new path) or deleted (null) from its menu. */
  onFileChanged?: (path: string | null) => void;
  /** Sends a message in the conversation, for Refresh. */
  onSend?: (text: string) => void;
  busy?: boolean;
}) {
  const dock = useDockPanel();
  const [menu, setMenu] = useState<DOMRect | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [info, setInfo] = useState<DashboardInfo | null>(null);
  useEffect(() => {
    let live = true;
    dashboardInfo(threadId, path)
      .then((found) => live && setInfo(found))
      .catch(() => live && setInfo(null));
    return () => {
      live = false;
    };
  }, [threadId, path, refreshKey]);
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
        {info && (
          <span className="truncate text-xs text-[var(--muted)]" title={info.datasets.map((d) => `${d.title}: ${d.source ?? "source not named"}`).join("\n")}>
            {info.error ? "The data could not be read" : dataTime(info) ? `Data from ${dataTime(info)}` : "Data time not given"}
          </span>
        )}
        {info && onSend && (
          <button
            type="button"
            disabled={busy}
            className="flex shrink-0 items-center gap-1.5 rounded-lg px-2 py-1 text-xs hover:bg-[var(--card-bg)] disabled:opacity-50"
            title="Ask coscribe to read the sources again and rewrite the data"
            onClick={() => onSend(`Refresh the dashboard ${path}: read its sources again and rewrite its data files, leaving the page as it is.`)}
          >
            <ReloadIcon className="h-3.5 w-3.5" />
            Refresh
          </button>
        )}
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
