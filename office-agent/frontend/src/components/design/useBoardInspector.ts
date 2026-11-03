import { useEffect, useRef, useState, type RefObject } from "react";
import {
  boardElementSteps,
  editBoardElement,
  inspectorAnswer,
  partNote,
  stepBoardElement,
  type ElementChange,
  type InspectedElement,
  type InspectedNode,
  type Steps,
} from "../../lib/boardInspector";

/** What the board's frame answers, kept with the board and page version it came from so another
 * board or a reloaded page shows nothing stale. The tree is asked for again whenever the page loads
 * anew; once it answers, an element waiting to be picked again (after a save) or a double click's
 * point is asked for. */
function useFrameAnswers(root: RefObject<HTMLDivElement | null>, open: boolean, boardId: string | null, version: string) {
  const repick = useRef<string | null>(null);
  // A double click's point, picked once the board's page answers (the panel may only now be opening),
  // and whether the element it finds is to have its text edited where it is drawn.
  const pickLater = useRef<{ x: number; y: number } | null>(null);
  const editNext = useRef(false);
  const [editing, setEditing] = useState<{ key: string; path: string } | null>(null);
  const [tree, setTree] = useState<{ key: string; tree: InspectedNode } | null>(null);
  const [element, setElement] = useState<{ key: string; element: InspectedElement | null } | null>(null);
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
        else if (pickLater.current) target.contentWindow?.postMessage({ coscribe: "inspect-pick", ...pickLater.current }, "*");
        repick.current = null;
        pickLater.current = null;
      } else if (answer) {
        setElement({ key: answered, element: answer.element });
        const found = answer.element;
        if (editNext.current && found && found.content !== null && !found.part) {
          setEditing({ key: answered, path: found.path });
          target.contentWindow?.postMessage({ coscribe: "inspect-hide-text", path: found.path, hidden: true }, "*");
        }
        editNext.current = false;
      }
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
  return { tree, element, repick, pickLater, editNext, editing, setEditing };
}

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
  const [problem, setProblem] = useState<string | null>(null);
  // What the server says can be undone and redone on the page, asked again whenever it is served anew
  // (coscribe writing the page ends them).
  const [steps, setSteps] = useState<{ key: string; steps: Steps } | null>(null);
  const [open, setOpen] = useState(false);
  const key = `${boardId}|${version}`;
  const frame = () => (boardId ? (root.current?.querySelector<HTMLIFrameElement>(`iframe[data-board="${CSS.escape(boardId)}"]`) ?? null) : null);
  const ask = (message: object) => frame()?.contentWindow?.postMessage(message, "*");

  const { tree, element, repick, pickLater, editNext, editing, setEditing } = useFrameAnswers(root, open, boardId, version);

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

  const shownElement = element?.key === key ? element.element : null;
  const editingText = shownElement && editing?.key === key && editing.path === shownElement.path ? shownElement : null;

  const edit = (target: InspectedElement, change: ElementChange) => {
    if (!board) return;
    if (target.part) {
      setProblem(partNote(target.part));
      return;
    }
    setProblem(null);
    editBoardElement(saving.threadId, board.path, target, change).then(
      () => {
        repick.current = target.path;
        saving.onSaved();
      },
      (e: unknown) => {
        setProblem(e instanceof Error ? e.message : String(e));
        ask({ coscribe: "inspect-hide-text", path: target.path, hidden: false });
      },
    );
  };

  return {
    open,
    setOpen,
    tree: tree?.key === key ? tree.tree : null,
    element: shownElement,
    pick: (x: number, y: number) => ask({ coscribe: "inspect-pick", x, y }),
    select: (path: string) => ask({ coscribe: "inspect-select", path }),
    problem,
    edit,
    /** A double click on the board: the element there is picked and, if it holds text alone, edited
     * where it is drawn. */
    editTextAt: (x: number, y: number) => {
      editNext.current = true;
      if (open && tree?.key === key) ask({ coscribe: "inspect-pick", x, y });
      else {
        pickLater.current = { x, y };
        setOpen(true);
      }
    },
    editingText,
    /** The text typed in place, or null to leave the page as it was. */
    finishText: (text: string | null) => {
      setEditing(null);
      if (!editingText) return;
      if (text === null || text === editingText.content) ask({ coscribe: "inspect-hide-text", path: editingText.path, hidden: false });
      else edit(editingText, { text });
    },
    canUndo: shown.undo > 0,
    canRedo: shown.redo > 0,
    undo: () => step("undo"),
    redo: () => step("redo"),
  };
}
