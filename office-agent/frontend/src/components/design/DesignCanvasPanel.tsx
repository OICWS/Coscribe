import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { readCanvas, type Canvas } from "../../lib/designCanvas";
import { PanelFileMenu } from "../artifacts/PanelFileMenu";
import { PanelTitleButton } from "../artifacts/PanelTitleButton";
import { useDockPanel } from "../dock/dockContext";
import { FullScreenPlayer } from "./BoardPlay";
import { BoardFrame, CanvasTools, CanvasZoom, NoteCard } from "./CanvasParts";
import { CanvasVariables } from "./CanvasVariables";
import { useBoardLinks } from "./useBoardLinks";
import { useBoardPlay } from "./useBoardPlay";
import { useCanvasEditing, type Tool } from "./useCanvasEditing";
import { useCanvasLook } from "./useCanvasLook";
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
function CanvasHeader({ threadId, path, problem, onFileChanged }: { threadId: string; path: string; problem: string | null; onFileChanged?: (path: string | null) => void }) {
  const dock = useDockPanel();
  const [menu, setMenu] = useState<DOMRect | null>(null);
  const name = path.split(/[\\/]/).pop() ?? path;
  return (
    <>
      {menu && <PanelFileMenu anchor={menu} threadId={threadId} path={path} onFileChanged={onFileChanged} onClose={() => setMenu(null)} />}
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

/** A Design canvas beside the conversation: its artboards, each its own page in a sandboxed frame,
 * laid out on a canvas the person pans and zooms. Boards and notes move with the select tool and
 * the moves are saved to the canvas file; a board played hands the pointer to its own page. */
export function DesignCanvasPanel({ threadId, path, refreshKey, onFileChanged }: { threadId: string; path: string; refreshKey: string; onFileChanged?: (path: string | null) => void }) {
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
  const hasVariables = Boolean(canvas?.variables.length);

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
      <CanvasHeader threadId={threadId} path={path} problem={problem} onFileChanged={onFileChanged} />
      <div ref={area} className="relative min-h-0 flex-1 overflow-hidden bg-[var(--card-bg)]">
        <CanvasTools tool={tool} onTool={setTool} />
        <CanvasZoom
          zoom={view.zoom}
          scheme={look.scheme}
          variablesOpen={hasVariables ? look.variablesOpen : undefined}
          onPlay={() => canvas?.boards.length && play.play(selected ?? canvas.boards[0].id, "full")}
          onZoom={zoomBy}
          onFit={fit}
          onScheme={look.setScheme}
          onVariables={() => look.setVariablesOpen((open) => !open)}
        />
        {hasVariables && look.variablesOpen && <CanvasVariables variables={canvas!.variables} onSet={look.setVariable} onClose={() => look.setVariablesOpen(false)} />}
        <div
          ref={stage}
          data-testid="canvas-stage"
          className={`absolute inset-0 ${panning ? "cursor-grab" : tool === "note" ? "cursor-crosshair" : ""}`}
          onPointerDown={onStageDown}
          onPointerMove={edit.move}
          onPointerUp={edit.end}
        >
          <div className="absolute left-0 top-0 origin-top-left" style={{ transform: `scale(${view.zoom}) translate(${-view.x}px, ${-view.y}px)` }}>
            {canvas?.boards.map((board) => (
              <BoardFrame
                key={board.id}
                board={board}
                threadId={threadId}
                version={`${refreshKey}.${look.served}`}
                zoom={view.zoom}
                live={play.live.includes(board.id)}
                selected={selected === board.id}
                scheme={look.scheme}
                onPress={(e) => {
                  if (panning || tool === "note") return;
                  setSelected(board.id);
                  edit.start(e, "board", board.id);
                }}
                onPlay={(mode) => play.play(board.id, mode)}
                onEdit={() => play.edit(board.id)}
              />
            ))}
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
        {play.fullBoard && <FullScreenPlayer board={play.fullBoard} threadId={threadId} version={`${refreshKey}.${look.served}`} scheme={look.scheme} onClose={play.stop} />}
      </div>
    </div>
  );
}
