import { useEffect, useState, type RefObject } from "react";

const PX_PER_PT = 96 / 72;
const GUTTER = 32;

/** How far a page of the given width (points) is scaled down to fit its scroller; never up. */
export function useSheetZoom(scroller: RefObject<HTMLElement | null>, widthPt: number | undefined): number {
  const [zoom, setZoom] = useState(1);
  useEffect(() => {
    const element = scroller.current;
    if (!element || !widthPt) return;
    const fit = () => setZoom(Math.max(0.3, Math.min(1, (element.clientWidth - GUTTER) / (widthPt * PX_PER_PT))));
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(element);
    return () => observer.disconnect();
  }, [scroller, widthPt]);
  return zoom;
}
