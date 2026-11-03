import { exportBoard, type BoardExport } from "../../lib/designExport";
import type { CanvasBoard } from "../../lib/designCanvas";
import { DownloadIcon } from "../icons";
import type { MenuEntry } from "../slides/SlideMenu";

const tile = (text: string) => (
  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[10px] font-bold text-[var(--muted)]">
    {text}
  </span>
);

/** The canvas file menu's Export: the selected artboard (or the first) as a PNG, or as an icon when
 * it is square, in the scheme the canvas shows. */
export function boardExports(threadId: string, canvasPath: string, board: CanvasBoard | null, scheme: "light" | "dark", onProblem: (problem: string | null) => void): MenuEntry[] {
  if (!board) return [];
  const stem = `${(canvasPath.split(/[\\/]/).pop() ?? canvasPath).replace(/\.design\.json$/i, "")}-${board.id}`;
  const run = (kind: BoardExport) => {
    onProblem(null);
    exportBoard(threadId, board.path, kind, scheme, stem).catch((e: unknown) => onProblem(e instanceof Error ? e.message : String(e)));
  };
  const square = board.width === board.height;
  return [
    {
      label: "Export",
      icon: <DownloadIcon className="h-4 w-4" />,
      submenu: [
        {
          label: "PNG",
          description: `“${board.title}” at twice its size`,
          icon: tile("PNG"),
          trailing: <DownloadIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />,
          onSelect: () => run("png"),
        },
        {
          label: "ICO",
          description: square ? `“${board.title}” as a Windows icon` : "For a square artboard",
          icon: tile("ICO"),
          disabled: !square,
          trailing: <DownloadIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />,
          onSelect: () => run("ico"),
        },
      ],
    },
  ];
}
