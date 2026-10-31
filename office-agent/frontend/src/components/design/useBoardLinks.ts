import { useEffect, useRef, type RefObject } from "react";
import type { Canvas, CanvasBoard } from "../../lib/designCanvas";

/** A link from one played artboard to another: the page hands the click over (`BOARD_LINKS` on
 * the server), since its sandbox can't navigate. Only a message from one of this canvas's own
 * frames counts, and the frame says which board sent it. */
export function useBoardLinks(root: RefObject<HTMLDivElement | null>, canvas: Canvas | null, onGo: (from: string, to: CanvasBoard) => void) {
  const go = useRef(onGo);
  useEffect(() => {
    go.current = onGo;
  });
  useEffect(() => {
    if (!canvas) return;
    const onMessage = (e: MessageEvent) => {
      const data = e.data as { coscribe?: unknown; file?: unknown } | null;
      const el = root.current;
      if (!el || data?.coscribe !== "go" || typeof data.file !== "string") return;
      const frame = [...el.querySelectorAll("iframe")].find((f) => f.contentWindow === e.source);
      if (!frame) return;
      const file = data.file.toLowerCase();
      const board = canvas.boards.find((b) => b.file.toLowerCase() === file);
      if (board) go.current(frame.dataset.board ?? "", board);
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [root, canvas]);
}
