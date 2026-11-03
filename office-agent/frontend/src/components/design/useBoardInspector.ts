import { useEffect, useRef, useState, type RefObject } from "react";
import { editBoardElement, inspectorAnswer, undoBoardElement, type ElementChange, type InspectedElement, type InspectedNode } from "../../lib/boardInspector";

/** The inspector of the selected artboard: its page's element tree, and the element picked on the
 * board or in the tree. Questions go to that board's frame and only its answers count; the tree
 * is asked for again whenever the page loads anew. An edit writes the page, serves it anew and
 * picks the same element again once the new page answers. */
export function useBoardInspector(
  root: RefObject<HTMLDivElement | null>,
  board: { id: string; path: string } | null,
  version: string,
  saving: { threadId: string; onSaved: () => void },
) {
  const boardId = board?.id ?? null;
  const repick = useRef<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  // Edits the panel wrote to each page in this view, which undo can take back.
  const [undoable, setUndoable] = useState<Record<string, number>>({});
  const [open, setOpen] = useState(false);
  // Answers are kept with the board and page version they came from, so another board or a reloaded
  // page shows nothing stale.
  const key = `${boardId}|${version}`;
  const [tree, setTree] = useState<{ key: string; tree: InspectedNode } | null>(null);
  const [element, setElement] = useState<{ key: string; element: InspectedElement | null } | null>(null);
  const frame = () => (boardId ? (root.current?.querySelector<HTMLIFrameElement>(`iframe[data-board="${CSS.escape(boardId)}"]`) ?? null) : null);
  const ask = (message: object) => frame()?.contentWindow?.postMessage(message, "*");

  useEffect(() => {
    if (!open || !boardId) return;
    const answered = `${boardId}|${version}`;
    const target = root.current?.querySelector<HTMLIFrameElement>(`iframe[data-board="${CSS.escape(boardId)}"]`);
    if (!target) return;
    const onMessage = (e: MessageEvent) => {
      if (e.source !== target.contentWindow) return;
      const answer = inspectorAnswer(e.data);
      if (answer && "tree" in answer) {
        setTree({ key: answered, tree: answer.tree });
        if (repick.current !== null) target.contentWindow?.postMessage({ coscribe: "inspect-select", path: repick.current }, "*");
        repick.current = null;
      } else if (answer) setElement({ key: answered, element: answer.element });
    };
    // A page still loading has no listener yet; its load asks again.
    const askTree = () => target.contentWindow?.postMessage({ coscribe: "inspect-tree" }, "*");
    window.addEventListener("message", onMessage);
    target.addEventListener("load", askTree);
    askTree();
    return () => {
      window.removeEventListener("message", onMessage);
      target.removeEventListener("load", askTree);
    };
  }, [root, open, boardId, version]);

  return {
    open,
    setOpen,
    tree: tree?.key === key ? tree.tree : null,
    element: element?.key === key ? element.element : null,
    pick: (x: number, y: number) => ask({ coscribe: "inspect-pick", x, y }),
    select: (path: string) => ask({ coscribe: "inspect-select", path }),
    problem,
    edit: (target: InspectedElement, change: ElementChange) => {
      if (!board) return;
      setProblem(null);
      editBoardElement(saving.threadId, board.path, target, change).then(
        () => {
          repick.current = target.path;
          setUndoable((counts) => ({ ...counts, [board.path]: (counts[board.path] ?? 0) + 1 }));
          saving.onSaved();
        },
        (e: unknown) => setProblem(e instanceof Error ? e.message : String(e)),
      );
    },
    canUndo: Boolean(board && undoable[board.path]),
    undo: () => {
      if (!board) return;
      setProblem(null);
      const keep = element?.key === key ? (element.element?.path ?? null) : null;
      const settle = (left: number) => setUndoable((counts) => ({ ...counts, [board.path]: left }));
      undoBoardElement(saving.threadId, board.path).then(
        (left) => {
          repick.current = keep;
          settle(left);
          saving.onSaved();
        },
        (e: unknown) => {
          settle(0);
          setProblem(e instanceof Error ? e.message : String(e));
        },
      );
    },
  };
}
