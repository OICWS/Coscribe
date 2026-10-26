import { useEffect, useRef, type RefObject } from "react";

/** How far from the end (in px) a log still counts as "at the end" and follows what is added. */
const FOLLOW_WITHIN_PX = 80;

/** Keeps a log scrolled to its end while the person is at the end, and leaves it alone once they
 * scroll up to read: an approval card or a streamed line then stays below the fold instead of
 * pulling the view down. `mine` (the person just sent something) always brings the end back.
 * Returns the scroll handler for the log's scroll box. */
export function useFollowEnd(scroller: RefObject<HTMLElement | null>, end: RefObject<HTMLElement | null>, changed: unknown, mine: boolean) {
  const following = useRef(true);
  useEffect(() => {
    if (!following.current && !mine) return;
    following.current = true;
    end.current?.scrollIntoView({ block: "end" });
  }, [changed, mine, end]);
  return () => {
    const el = scroller.current;
    if (el) following.current = el.scrollHeight - el.scrollTop - el.clientHeight < FOLLOW_WITHIN_PX;
  };
}
