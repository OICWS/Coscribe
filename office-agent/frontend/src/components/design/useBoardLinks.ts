import { useEffect, type Dispatch, type RefObject, type SetStateAction } from "react";
import { fitView, type Canvas, type View } from "../../lib/designCanvas";

/** In Play, a link from one artboard to another shows that board, fitted to the panel: the page
 * hands the click over (`BOARD_LINKS` on the server), since its sandbox can't navigate. Only a
 * message from one of this canvas's own frames counts. */
export function useBoardLinks(stage: RefObject<HTMLDivElement | null>, canvas: Canvas | null, playing: boolean, setView: Dispatch<SetStateAction<View>>) {
  useEffect(() => {
    if (!playing || !canvas) return;
    const onMessage = (e: MessageEvent) => {
      const data = e.data as { coscribe?: unknown; file?: unknown } | null;
      const el = stage.current;
      if (!el || data?.coscribe !== "go" || typeof data.file !== "string") return;
      if (![...el.querySelectorAll("iframe")].some((frame) => frame.contentWindow === e.source)) return;
      const file = data.file.toLowerCase();
      const board = canvas.boards.find((b) => b.file.toLowerCase() === file);
      if (board) setView(fitView({ boards: [board], variables: [], notes: [] }, el.clientWidth, el.clientHeight));
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [stage, canvas, playing, setView]);
}
