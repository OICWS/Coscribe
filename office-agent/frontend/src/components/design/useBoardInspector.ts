import { useEffect, useState, type RefObject } from "react";
import { inspectorAnswer, type InspectedElement, type InspectedNode } from "../../lib/boardInspector";

/** The inspector of the selected artboard: its page's element tree, and the element picked on the
 * board or in the tree. Questions go to that board's frame and only its answers count; the tree
 * is asked for again whenever the page loads anew. */
export function useBoardInspector(root: RefObject<HTMLDivElement | null>, boardId: string | null, version: string) {
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
      if (answer && "tree" in answer) setTree({ key: answered, tree: answer.tree });
      else if (answer) setElement({ key: answered, element: answer.element });
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
  };
}
