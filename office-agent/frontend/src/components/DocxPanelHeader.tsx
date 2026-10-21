import { useState, type ReactNode } from "react";
import { PanelFileMenu } from "./artifacts/PanelFileMenu";
import { PanelTitleButton } from "./artifacts/PanelTitleButton";
import { useDockPanel } from "./dock/dockContext";
import { PencilIcon } from "./icons";

/** A Word file's panel header: its name with the file menu, then what the panel adds, then the dock's controls. */
export function DocxPanelHeader({
  threadId,
  path,
  onFileChanged,
  onEdit,
  children,
}: {
  threadId: string;
  path: string;
  onFileChanged?: (path: string | null) => void;
  /** Offers the editor: a button that calls this. */
  onEdit?: () => void;
  children?: ReactNode;
}) {
  const dock = useDockPanel();
  const [menu, setMenu] = useState<DOMRect | null>(null);
  const name = path.split(/[\\/]/).pop() ?? path;
  return (
    <>
      {menu && <PanelFileMenu anchor={menu} threadId={threadId} path={path} onFileChanged={onFileChanged} onClose={() => setMenu(null)} />}
      <div className="flex h-12 shrink-0 items-center gap-2 px-3" {...dock.headerProps}>
        <PanelTitleButton title={name} path={path} onMenu={setMenu} />
        <div className="flex-1" />
        {children}
        {onEdit && (
          <button type="button" className="flex h-7 items-center gap-1.5 rounded-lg border border-[var(--border)] px-2.5 text-xs text-[var(--fg)] hover:bg-[var(--card-bg)]" onClick={onEdit}>
            <PencilIcon className="h-3.5 w-3.5" />
            Edit
          </button>
        )}
        {dock.controls}
      </div>
    </>
  );
}
