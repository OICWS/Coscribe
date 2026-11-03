import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { readCanvas, type Canvas } from "../../lib/designCanvas";
import { PanelFileMenu } from "../artifacts/PanelFileMenu";
import { PanelTitleButton } from "../artifacts/PanelTitleButton";
import { useDockPanel } from "../dock/dockContext";
import { FullScreenPlayer } from "./BoardPlay";
import { BoardInspector } from "./BoardInspector";
import { BoardTextEditor } from "./BoardTextEditor";
import { boardExports } from "./boardExports";
import type { MenuEntry } from "../slides/SlideMenu";
import { BoardFrame, CanvasTools, CanvasZoom, NoteCard } from "./CanvasParts";
import { CanvasVariables } from "./CanvasVariables";
import { useBoardInspector } from "./useBoardInspector";
import { useBoardLinks } from "./useBoardLinks";
import { useBoardPlay } from "./useBoardPlay";
import { useCanvasEditing, type Tool } from "./useCanvasEditing";
import { useCanvasLook, type Scheme } from "./useCanvasLook";
import { useCanvasView } from "./useCanvasView";

/** Space held turns any tool into the hand, as long as no text is being typed; Escape stops playing. */
function useKeys(onEscape: () => void) {
  const [spaceHeld, setSpaceHeld] = useState(false);
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement && /^(INPUT|TEXTAREA)$/.test(e.target.tagName)) return;
      if (e.code === "Space") setSpaceHeld(true);
      if (e.key === "Escape") onEscape();
    };
    const up = (e: KeyboardEvent) => e.code === "Space" && setSpaceHeld(false);
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  }, [onEscape]);
  return spaceHeld;
}

/** The canvas file, read again whenever a turn writes a file, and what went wrong with it. */
function useCanvasFile(threadId: string, path: string, version: string) {
  const [canvas, setCanvas] = useState<Canvas | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    readCanvas(threadId, path)
      .then((found) => {
        if (!live) return;
        setCanvas(found);
        setProblem(null);
      })
      .catch((e: unknown) => live && setProblem(e instanceof Error ? e.message : String(e)));
    return () => {
      live = false;
    };
  }, [threadId, path, version]);
  return { canvas, setCanvas, problem, setProblem };
}

/** The panel's title (with the file menu), what went wrong with the canvas, and the dock's controls. */
function CanvasHeader({
  threadId,
  path,
  problem,
  exports,
  onFileChanged,
}: {
  threadId: string;
  path: string;
  problem: string | null;
  exports: MenuEntry[];
  onFileChanged?: (path: string | null) => void;
}) {
  const dock = useDockPanel();
  const [menu, setMenu] = useState<DOMRect | null>(null);
  const name = path.split(/[\\/]/).pop() ?? path;
  return (
    <>
      {menu && <PanelFileMenu anchor={menu} threadId={threadId} path={path} extra={exports} onFileChanged={onFileChanged} onClose={() => setMenu(null)} />}
      <div className="flex h-12 shrink-0 items-center gap-2 px-3" {...dock.headerProps}>
        <PanelTitleButton title={name.replace(/\.design\.json$/i, "")} path={path} onMenu={setMenu} />
        <div className="flex-1" />
        {problem && (
          <span className="max-w-[40%] truncate text-xs text-[var(--danger)]" role="alert" title={problem}>
            {problem}
          </span>
        )}
        {dock.controls}
      </div>
    </>
  );
}

/** The top-right bar and the variables it opens. */
function CanvasBars({
  canvas,
  zoom,
  look,
  inspector,
  onPlay,
  onZoom,
  onFit,
}: {
  canvas: Canvas | null;
  zoom: number;
  look: ReturnType<typeof useCanvasLook>;
  inspector: ReturnType<typeof useBoardInspector>;
  onPlay: () => void;
  onZoom: (factor: number) => void;
  onFit: () => void;
}) {
  const hasVariables = Boolean(canvas?.variables.length);
  return (
    <>
      <CanvasZoom
        zoom={zoom}
        scheme={look.scheme}
        variablesOpen={hasVariables ? look.variablesOpen : undefined}
        propertiesOpen={inspector.open}
        onPlay={onPlay}
        onZoom={onZoom}
        onFit={onFit}
        onScheme={look.setScheme}
        onVariables={() => look.setVariablesOpen((open) => !open)}
        onProperties={() => inspector.setOpen((open) => !open)}
      />
      {hasVariables && look.variablesOpen && <CanvasVariables variables={canvas!.variables} onSet={look.setVariable} onClose={() => look.setVariablesOpen(false)} />}
    </>
  );
}

/** Every artboard on the canvas, with what playing and inspecting do to it. */
function CanvasBoards({
  canvas,
  threadId,
  version,
  zoom,
  scheme,
  selected,
  play,
  inspector,
  onPress,
}: {
  canvas: Canvas;
  threadId: string;
  version: string;
  zoom: number;
  scheme: Scheme;
  selected: string | null;
  play: ReturnType<typeof useBoardPlay>;
  inspector: ReturnType<typeof useBoardInspector>;
  onPress: (e: ReactPointerEvent, id: string) => void;
}) {
  return canvas.boards.map((board) => (
    <BoardFrame
      key={board.id}
      board={board}
      threadId={threadId}
      version={version}
      zoom={zoom}
      live={play.live.includes(board.id)}
      selected={selected === board.id}
      scheme={scheme}
      onPress={(e) => onPress(e, board.id)}
      onPlay={(mode) => play.play(board.id, mode)}
      onEdit={() => play.edit(board.id)}
      onPick={inspector.open ? inspector.pick : undefined}
      onEditText={inspector.editTextAt}
      highlight={inspector.open && selected === board.id && !inspector.editingText ? inspector.element?.box : null}
    >
      {selected === board.id && inspector.editingText && <BoardTextEditor key={inspector.editingText.path} element={inspector.editingText} onDone={inspector.finishText} />}
    </BoardFrame>
  ));
}

/** The properties panel beside the canvas, for the selected artboard. */
function InspectorAside({ canvas, selected, inspector }: { canvas: Canvas | null; selected: string | null; inspector: ReturnType<typeof useBoardInspector> }) {
  return (
    <BoardInspector
      boardTitle={canvas?.boards.find((b) => b.id === selected)?.title ?? null}
      tree={inspector.tree}
      element={inspector.element}
      problem={inspector.problem}
      onSelect={inspector.select}
      onEdit={(change) => inspector.element && inspector.edit(inspector.element, change)}
      canUndo={inspector.canUndo}
      onUndo={inspector.undo}
      canRedo={inspector.canRedo}
      onRedo={inspector.redo}
      onClose={() => inspector.setOpen(false)}
    />
  );
}

interface PanelProps {
  threadId: string;
  path: string;
  refreshKey: string;
  onFileChanged?: (path: string | null) => void;
}

/** A Design canvas beside the conversation: its artboards, each its own page in a sandboxed frame,
 * laid out on a canvas the person pans and zooms. Boards and notes move with the select tool and
 * the moves are saved to the canvas file; a board played hands the pointer to its own page. */
export function DesignCanvasPanel({ threadId, path, refreshKey, onFileChanged }: PanelProps) {
  const stage = useRef<HTMLDivElement>(null);
  const { canvas, setCanvas, problem, setProblem } = useCanvasFile(threadId, path, refreshKey);
  const [tool, setTool] = useState<Tool>("select");
  const [selected, setSelected] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const area = useRef<HTMLDivElement>(null);
  const { view, setView, fit, zoomBy, toCanvas } = useCanvasView(stage, canvas);
  const stageSize = () => (stage.current ? { width: stage.current.clientWidth, height: stage.current.clientHeight } : null);
  const play = useBoardPlay(canvas, stageSize, setView);
  const spaceHeld = useKeys(play.stop);
  const edit = useCanvasEditing({ threadId, path, canvas, setCanvas, view, setView, toCanvas, onProblem: setProblem });
  const look = useCanvasLook(threadId, path, setCanvas, setProblem);
  useBoardLinks(area, canvas, play.go);
  const version = `${refreshKey}.${look.served}`;
  const inspected = canvas?.boards.find((b) => b.id === selected) ?? null;
  const inspector = useBoardInspector(area, inspected, `${version}.${look.scheme}`, { threadId, onSaved: look.reload });

  const panning = tool === "hand" || spaceHeld;
  const onStageDown = (e: ReactPointerEvent) => {
    if (!canvas) return;
    setSelected(null);
    setEditing(null);
    if (tool === "note" && e.button === 0) {
      setEditing(edit.addNote(e));
      setTool("select");
    } else {
      edit.start(e, "pan");
    }
  };
  return (
    <div className="flex h-full min-h-0 flex-col">
      <CanvasHeader
        threadId={threadId}
        path={path}
        problem={problem}
        exports={boardExports(threadId, path, inspected ?? canvas?.boards[0] ?? null, look.scheme, setProblem)}
        onFileChanged={onFileChanged}
      />
      <div className="flex min-h-0 flex-1">
        <div ref={area} className="relative min-w-0 flex-1 overflow-hidden bg-[var(--card-bg)]">
          <CanvasTools tool={tool} onTool={setTool} />
          <CanvasBars
            canvas={canvas}
            zoom={view.zoom}
            look={look}
            inspector={inspector}
            onPlay={() => canvas?.boards.length && play.play(selected ?? canvas.boards[0].id, "full")}
            onZoom={zoomBy}
            onFit={fit}
          />
          <div
            ref={stage}
            data-testid="canvas-stage"
            className={`absolute inset-0 ${panning ? "cursor-grab" : tool === "note" ? "cursor-crosshair" : ""}`}
            onPointerDown={onStageDown}
            onPointerMove={edit.move}
            onPointerUp={edit.end}
          >
            <div className="absolute left-0 top-0 origin-top-left" style={{ transform: `scale(${view.zoom}) translate(${-view.x}px, ${-view.y}px)` }}>
              {canvas && (
                <CanvasBoards
                  canvas={canvas}
                  threadId={threadId}
                  version={version}
                  zoom={view.zoom}
                  scheme={look.scheme}
                  selected={selected}
                  play={play}
                  inspector={inspector}
                  onPress={(e, id) => {
                    if (panning || tool === "note") return;
                    setSelected(id);
                    edit.start(e, "board", id);
                  }}
                />
              )}
              {canvas?.notes.map((note) => (
                <NoteCard
                  key={note.id}
                  note={note}
                  editing={editing === note.id}
                  onPress={(e) => !panning && edit.start(e, "note", note.id)}
                  onEdit={() => setEditing(note.id)}
                  onDone={(text) => {
                    setEditing(null);
                    edit.editNote(note.id, text);
                  }}
                />
              ))}
            </div>
          </div>
          {play.fullBoard && <FullScreenPlayer board={play.fullBoard} threadId={threadId} version={version} scheme={look.scheme} onClose={play.stop} />}
        </div>
        {inspector.open && <InspectorAside canvas={canvas} selected={selected} inspector={inspector} />}
      </div>
    </div>
  );
}
