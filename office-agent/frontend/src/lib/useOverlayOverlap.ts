import { useEffect, useState, type RefObject } from "react";

/** Native browser views only step aside for popovers that cover their page area. */
export function useOverlayOverlap(area: RefObject<HTMLElement | null>): boolean {
  const [overlaps, setOverlaps] = useState(false);
  useEffect(() => {
    let frame = 0;
    const check = () => {
      frame = 0;
      const popups = document.querySelectorAll<HTMLElement>("[data-native-overlay]");
      const page = popups.length ? area.current?.getBoundingClientRect() : null;
      setOverlaps(Boolean(page && page.width > 0 && page.height > 0 &&
        [...popups].some(element => {
          const popup = element.getBoundingClientRect();
          return popup.width > 0 && popup.height > 0 && popup.left < page.right &&
            popup.right > page.left && popup.top < page.bottom && popup.bottom > page.top;
        })));
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(check); };
    const changes = new MutationObserver(schedule);
    changes.observe(document.body, { childList: true, subtree: true, characterData: true,
      attributes: true, attributeFilter: ["class", "style", "hidden"] });
    const resize = new ResizeObserver(schedule);
    if (area.current) resize.observe(area.current);
    window.addEventListener("resize", schedule);
    window.addEventListener("scroll", schedule, true);
    check();
    return () => {
      changes.disconnect();
      resize.disconnect();
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", schedule);
      window.removeEventListener("scroll", schedule, true);
    };
  }, [area]);
  return overlaps;
}
