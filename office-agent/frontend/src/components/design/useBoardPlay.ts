import { useState, type Dispatch, type SetStateAction } from "react";
import { fitView, type Canvas, type CanvasBoard, type View } from "../../lib/designCanvas";

export type PlayMode = "canvas" | "full";

/** Which artboards are being used rather than edited: any number on the canvas, each where it
 * stands, or one filling the panel. A link from a played board shows its target the same way. */
export function useBoardPlay(canvas: Canvas | null, stageSize: () => { width: number; height: number } | null, setView: Dispatch<SetStateAction<View>>) {
  const [live, setLive] = useState<string[]>([]);
  const [full, setFull] = useState<string | null>(null);
  const [stop] = useState(() => () => {
    setLive([]);
    setFull(null);
  });
  const play = (id: string, mode: PlayMode) => (mode === "full" ? setFull(id) : setLive((ids) => (ids.includes(id) ? ids : [...ids, id])));
  const edit = (id: string) => setLive((ids) => ids.filter((other) => other !== id));
  const go = (from: string, to: CanvasBoard) => {
    if (full !== null) return setFull(to.id);
    setLive((ids) => [...ids.filter((id) => id !== from && id !== to.id), to.id]);
    const size = stageSize();
    if (size) setView(fitView({ boards: [to], variables: [], notes: [] }, size.width, size.height));
  };
  const fullBoard = canvas?.boards.find((board) => board.id === full) ?? null;
  return { live, fullBoard, play, edit, go, stop };
}
