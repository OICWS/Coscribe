import { useLayoutEffect, useRef } from "react";
import type { InspectedElement } from "../../lib/boardInspector";

// What makes the typed text sit where the page draws it; the page's own copy is hidden meanwhile.
const TEXT_STYLE = ["font-family", "font-size", "font-weight", "font-style", "line-height", "letter-spacing", "text-align", "text-transform", "color", "padding"];

// The field grows with what is typed, as the page's element would.
function grow(el: HTMLTextAreaElement, minHeight: number) {
  el.style.height = "auto";
  el.style.height = `${Math.max(minHeight, el.scrollHeight)}px`;
}

/** The text of an element that holds text alone, edited where the board draws it: Enter or leaving
 * the field writes it, Shift+Enter starts a new line, Escape keeps the page as it was. */
export function BoardTextEditor({ element, onDone }: { element: InspectedElement; onDone: (text: string | null) => void }) {
  const field = useRef<HTMLTextAreaElement>(null);
  const done = useRef(false);
  const finish = (text: string | null) => {
    if (done.current) return;
    done.current = true;
    onDone(text);
  };
  const minHeight = element.box.height;
  useLayoutEffect(() => {
    const el = field.current;
    if (!el) return;
    grow(el, minHeight);
    el.focus();
    el.select();
  }, [minHeight]);
  const style: Record<string, string | number> = { left: element.box.x, top: element.box.y, width: element.box.width, minHeight };
  for (const name of TEXT_STYLE) {
    const value = element.computed[name];
    if (value) style[name.replace(/-([a-z])/g, (_, c: string) => c.toUpperCase())] = value;
  }
  return (
    <textarea
      ref={field}
      aria-label="Edit text"
      defaultValue={element.content ?? ""}
      rows={1}
      className="absolute z-20 m-0 resize-none overflow-hidden border-0 bg-transparent outline outline-2 outline-[var(--accent)]"
      style={style}
      onPointerDown={(e) => e.stopPropagation()}
      onInput={(e) => grow(e.currentTarget, minHeight)}
      onBlur={(e) => finish(e.currentTarget.value)}
      onKeyDown={(e) => {
        e.stopPropagation();
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          finish(e.currentTarget.value);
        } else if (e.key === "Escape") {
          e.preventDefault();
          finish(null);
        }
      }}
    />
  );
}
