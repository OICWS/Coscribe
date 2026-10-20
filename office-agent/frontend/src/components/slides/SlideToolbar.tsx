import { zoomLabel } from "../../lib/slides";
import { ChevronDownIcon, DownloadIcon, PlayIcon, RedoIcon, UndoIcon } from "../icons";
import { PropertiesBelowIcon, PropertiesBesideIcon } from "./slideIcons";

const toolButton = "flex h-8 w-8 items-center justify-center rounded-lg text-[var(--fg)] hover:bg-[var(--card-bg)]";
const toolButtonOn = "flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-ink)]";

/** The card at the stage's top right: Download, Present, the properties panel and the zoom menu, with undo and redo first. */
export function SlideToolbar({
  zoom,
  propertiesShown,
  beside,
  onToggleProperties,
  canUndo,
  canRedo,
  onStep,
  onZoomMenu,
  onPresentMenu,
  onDownloadMenu,
  busy,
}: {
  zoom: number;
  propertiesShown: boolean;
  beside: boolean;
  onToggleProperties: () => void;
  canUndo: boolean;
  canRedo: boolean;
  onStep: (action: "undo" | "redo") => void;
  onZoomMenu: (anchor: DOMRect) => void;
  onPresentMenu: (anchor: DOMRect) => void;
  onDownloadMenu: (anchor: DOMRect) => void;
  /** A download being made: the button shows it is working. */
  busy: boolean;
}) {
  return (
    <div className="absolute right-4 top-4 z-10 flex h-11 items-center gap-1 rounded-xl border border-[var(--border)] bg-[var(--bg)] px-1.5 shadow-[var(--panel-shadow)]">
      <button type="button" title="Undo (Ctrl+Z)" aria-label="Undo" disabled={!canUndo} className={`${toolButton} disabled:opacity-40`} onClick={() => onStep("undo")}>
        <UndoIcon className="h-[17px] w-[17px]" />
      </button>
      <button type="button" title="Redo (Ctrl+Shift+Z)" aria-label="Redo" disabled={!canRedo} className={`${toolButton} disabled:opacity-40`} onClick={() => onStep("redo")}>
        <RedoIcon className="h-[17px] w-[17px]" />
      </button>
      <span className="mx-1 h-5 border-l border-[var(--border)]" />
      <button
        type="button"
        title={busy ? "Preparing the download" : "Download"}
        aria-label="Download"
        aria-haspopup="menu"
        aria-busy={busy}
        disabled={busy}
        className={`${toolButton} disabled:animate-pulse`}
        onClick={(e) => onDownloadMenu(e.currentTarget.getBoundingClientRect())}
      >
        <DownloadIcon className="h-[17px] w-[17px]" />
      </button>
      <button
        type="button"
        title="Present"
        aria-label="Present"
        aria-haspopup="menu"
        className={toolButton}
        onClick={(e) => onPresentMenu(e.currentTarget.getBoundingClientRect())}
      >
        <PlayIcon className="h-[16px] w-[16px]" />
      </button>
      <span className="mx-1 h-5 border-l border-[var(--border)]" />
      <button
        type="button"
        title={propertiesShown ? "Hide the properties panel" : "Show the properties panel"}
        aria-label="Properties panel"
        aria-pressed={propertiesShown}
        className={propertiesShown ? toolButtonOn : toolButton}
        onClick={onToggleProperties}
      >
        {beside ? <PropertiesBesideIcon className="h-[18px] w-[18px]" /> : <PropertiesBelowIcon className="h-[18px] w-[18px]" />}
      </button>
      <span className="mx-1 h-5 border-l border-[var(--border)]" />
      <button
        type="button"
        aria-haspopup="menu"
        aria-label={`Zoom ${zoomLabel(zoom)}`}
        className="flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[15px] tabular-nums text-[var(--fg)] hover:bg-[var(--card-bg)]"
        onClick={(e) => onZoomMenu(e.currentTarget.getBoundingClientRect())}
      >
        {zoomLabel(zoom)}
        <ChevronDownIcon className="h-3.5 w-3.5 text-[var(--muted)]" />
      </button>
    </div>
  );
}
