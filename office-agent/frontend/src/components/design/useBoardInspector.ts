import { useEffect, useRef, useState, type RefObject } from "react";
import {
  boardElementSteps,
  editBoardElement,
  inspectorAnswer,
  stepBoardElement,
  type ElementChange,
  type InspectedElement,
  type InspectedNode,
  type Steps,
} from "../../lib/boardInspector";

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
  // What the server says can be undone and redone on the page, asked again whenever it is served anew
  // (coscribe writing the page ends them).
  const [steps, setSteps] = useState<{ key: string; steps: Steps } | null>(null);
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

  const page = board?.path ?? null;
  useEffect(() => {
    if (!open || !page) return;
    let live = true;
    boardElementSteps(saving.threadId, page).then((found) => live && setSteps({ key, steps: found }));
    return () => {
      live = false;
    };
  }, [open, page, key, saving.threadId]);
  const shown = steps?.key === key ? steps.steps : { undo: 0, redo: 0 };

  const step = (action: "undo" | "redo") => {
    if (!board) return;
    setProblem(null);
    const keep = element?.key === key ? (element.element?.path ?? null) : null;
    stepBoardElement(saving.threadId, board.path, action).then(
      () => {
        repick.current = keep;
        saving.onSaved();
      },
      (e: unknown) => setProblem(e instanceof Error ? e.message : String(e)),
    );
  };

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
          saving.onSaved();
        },
        (e: unknown) => setProblem(e instanceof Error ? e.message : String(e)),
      );
    },
    canUndo: shown.undo > 0,
    canRedo: shown.redo > 0,
    undo: () => step("undo"),
    redo: () => step("redo"),
  };
}
