import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { fitView, zoomAt, type Canvas, type View } from "../../lib/designCanvas";

/** Where the canvas is looked at from: fitted to its boards the first time they arrive, panned by
 * the wheel and zoomed with Ctrl or Cmd (a trackpad pinch) around the pointer. */
export function useCanvasView(stage: RefObject<HTMLDivElement | null>, canvas: Canvas | null) {
  const [view, setView] = useState<View>({ x: 0, y: 0, zoom: 1 });
  const fitted = useRef(false);

  const fit = useCallback(() => {
    const el = stage.current;
    if (el && canvas) setView(fitView(canvas, el.clientWidth, el.clientHeight));
  }, [canvas, stage]);

  useEffect(() => {
    if (canvas && !fitted.current) {
      fitted.current = true;
      fit();
    }
  }, [canvas, fit]);

  // Not passive, so the page behind does not scroll or zoom too. Over a played board its page takes it.
  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const box = el.getBoundingClientRect();
      if (e.ctrlKey || e.metaKey) setView((v) => zoomAt(v, Math.exp(-e.deltaY * 0.0015), e.clientX - box.left, e.clientY - box.top));
      else setView((v) => ({ ...v, x: v.x + e.deltaX / v.zoom, y: v.y + e.deltaY / v.zoom }));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [stage]);

  const zoomBy = (factor: number) => {
    const el = stage.current;
    if (el) setView((v) => zoomAt(v, factor, el.clientWidth / 2, el.clientHeight / 2));
  };

  /** The canvas point under a point of the window. */
  const toCanvas = (clientX: number, clientY: number) => {
    const box = stage.current!.getBoundingClientRect();
    return { x: view.x + (clientX - box.left) / view.zoom, y: view.y + (clientY - box.top) / view.zoom };
  };

  return { view, setView, fit, zoomBy, toCanvas };
}
