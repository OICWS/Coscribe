import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";
import { designFileUrl } from "../../lib/artifacts";
import type { CanvasBoard, CanvasNote } from "../../lib/designCanvas";
import { CursorClickIcon, HandIcon, MoonIcon, PauseIcon, PlayIcon, SunIcon } from "../icons";
import type { Tool } from "./useCanvasEditing";
import type { Scheme } from "./useCanvasLook";

const NOTE_FILL: Record<CanvasNote["color"], string> = { yellow: "#fff3b0", pink: "#ffd6e0", blue: "#d6e8ff", green: "#d8f5d0" };
const BAR = "absolute z-10 flex items-center gap-0.5 rounded-xl border border-[var(--border)] bg-[var(--panel-bg)] p-1 shadow-[var(--shadow)]";

function NoteIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" aria-hidden>
      <path d="M5 4h14v10l-6 6H5z" />
      <path d="M13 20v-6h6" />
    </svg>
  );
}

function SlidersIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden>
      <path d="M4 7h10M18 7h2M4 17h4M12 17h8" />
      <circle cx="16" cy="7" r="2" />
      <circle cx="10" cy="17" r="2" />
    </svg>
  );
}

function ToolButton({ label, active, onClick, children }: { label: string; active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={active}
      title={label}
      onClick={onClick}
      className={`flex h-8 w-8 items-center justify-center rounded-lg ${active ? "bg-[var(--accent)] text-white" : "hover:bg-[var(--card-bg)]"}`}
    >
      {children}
    </button>
  );
}

/** The tools at the canvas's top-left: Select, Hand, Note. */
export function CanvasTools({ tool, playing, onTool }: { tool: Tool; playing: boolean; onTool: (tool: Tool) => void }) {
  return (
    <div className={`${BAR} left-3 top-3`} role="toolbar" aria-label="Canvas tools">
      <ToolButton label="Select" active={tool === "select" && !playing} onClick={() => onTool("select")}>
        <CursorClickIcon className="h-4 w-4" />
      </ToolButton>
      <ToolButton label="Hand" active={tool === "hand" && !playing} onClick={() => onTool("hand")}>
        <HandIcon className="h-4 w-4" />
      </ToolButton>
      <ToolButton label="Note" active={tool === "note" && !playing} onClick={() => onTool("note")}>
        <NoteIcon className="h-4 w-4" />
      </ToolButton>
    </div>
  );
}

interface ZoomProps {
  zoom: number;
  playing: boolean;
  scheme: Scheme;
  /** Absent when the canvas declares no variables. */
  variablesOpen?: boolean;
  onPlay: () => void;
  onZoom: (factor: number) => void;
  onFit: () => void;
  onScheme: (scheme: Scheme) => void;
  onVariables: () => void;
}

/** The variables, light or dark, Play and the zoom, at the canvas's top-right; the percentage fits
 * everything. */
export function CanvasZoom({ zoom, playing, scheme, variablesOpen, onPlay, onZoom, onFit, onScheme, onVariables }: ZoomProps) {
  const plain = "h-8 rounded-lg px-2 hover:bg-[var(--card-bg)]";
  const dark = scheme === "dark";
  return (
    <div className={`${BAR} right-3 top-3`}>
      {variablesOpen !== undefined && (
        <ToolButton label="Variables" active={variablesOpen} onClick={onVariables}>
          <SlidersIcon className="h-4 w-4" />
        </ToolButton>
      )}
      <ToolButton label={dark ? "Show light" : "Show dark"} active={false} onClick={() => onScheme(dark ? "light" : "dark")}>
        {dark ? <SunIcon className="h-4 w-4" /> : <MoonIcon className="h-4 w-4" />}
      </ToolButton>
      <ToolButton label={playing ? "Stop playing" : "Play"} active={playing} onClick={onPlay}>
        {playing ? <PauseIcon className="h-4 w-4" /> : <PlayIcon className="h-4 w-4" />}
      </ToolButton>
      <button type="button" aria-label="Zoom out" className={plain} onClick={() => onZoom(1 / 1.25)}>
        −
      </button>
      <button type="button" title="Fit everything" className={`${plain} min-w-14 text-sm tabular-nums`} onClick={onFit}>
        {Math.round(zoom * 100)}%
      </button>
      <button type="button" aria-label="Zoom in" className={plain} onClick={() => onZoom(1.25)}>
        +
      </button>
    </div>
  );
}

/** One artboard: its page in a sandboxed frame at its real size and in the canvas's colour scheme, its title above it at a steady
 * size whatever the zoom, and, outside Play, a cover that takes the pointer for the canvas. */
export function BoardFrame({
  board,
  threadId,
  version,
  zoom,
  playing,
  selected,
  scheme,
  onPress,
}: {
  board: CanvasBoard;
  threadId: string;
  version: string;
  zoom: number;
  playing: boolean;
  selected: boolean;
  scheme: Scheme;
  onPress: (e: ReactPointerEvent) => void;
}) {
  return (
    <div className="absolute" style={{ left: board.x, top: board.y, width: board.width, height: board.height }}>
      <div
        className={`absolute bottom-full left-0 mb-1.5 origin-bottom-left truncate text-[13px] ${selected ? "text-[var(--accent)]" : "text-[var(--muted)]"}`}
        style={{ transform: `scale(${1 / zoom})`, maxWidth: board.width * zoom }}
      >
        {board.title}
      </div>
      <iframe
        key={`${board.path}.${version}.${scheme}`}
        title={board.title}
        src={designFileUrl(threadId, board.path, version, scheme)}
        sandbox="allow-scripts"
        className="h-full w-full border-0 bg-white shadow-sm"
        style={{ pointerEvents: playing ? "auto" : "none" }}
      />
      {!playing && (
        <div
          data-testid={`board-${board.id}`}
          className={`absolute inset-0 ${selected ? "outline outline-2 outline-[var(--accent)]" : "hover:outline hover:outline-1 hover:outline-[var(--accent)]"}`}
          onPointerDown={onPress}
        />
      )}
    </div>
  );
}

/** A note the person left on the canvas: dragged by its body, its text edited after a double click. */
export function NoteCard({
  note,
  editing,
  onPress,
  onEdit,
  onDone,
}: {
  note: CanvasNote;
  editing: boolean;
  onPress: (e: ReactPointerEvent) => void;
  onEdit: () => void;
  onDone: (text: string) => void;
}) {
  return (
    <div
      data-testid={`note-${note.id}`}
      className="absolute rounded-md p-3 text-[14px] leading-snug text-[#3a3320] shadow-md"
      style={{ left: note.x, top: note.y, width: note.width, background: NOTE_FILL[note.color] }}
      onPointerDown={onPress}
      onDoubleClick={onEdit}
    >
      {editing ? (
        <textarea
          aria-label="Note text"
          autoFocus
          defaultValue={note.text}
          className="block min-h-16 w-full resize-none bg-transparent outline-none"
          onPointerDown={(e) => e.stopPropagation()}
          onBlur={(e) => onDone(e.target.value)}
        />
      ) : (
        <div className="whitespace-pre-wrap">{note.text}</div>
      )}
    </div>
  );
}
