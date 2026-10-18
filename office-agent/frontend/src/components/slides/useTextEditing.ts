import { useEffect, useRef, useState } from "react";
import { elementsOf } from "../../lib/slideSource";
import { textNode, writeTextBack } from "./sectionDom";

type Change = (edit: (elements: Element[]) => void, redraw: boolean) => void;

/** Typing into one text element in place: its drawn text becomes editable, and when the typing
 * ends (Escape, or a press anywhere but the text and the format bar) the text is written back
 * into the section and saved. */
export function useTextEditing(
  doc: Document | null,
  nodes: { current: (HTMLElement | null)[] },
  change: Change,
) {
  const [typing, setTyping] = useState<number | null>(null);
  const typingRef = useRef<number | null>(null);

  const stop = () => {
    const at = typingRef.current;
    typingRef.current = null;
    setTyping(null);
    const edited = at === null ? null : textNode(nodes.current[at]);
    if (at === null || !edited || !doc) return;
    edited.contentEditable = "false";
    const el = elementsOf(doc)[at];
    const probe = el.cloneNode(false) as Element;
    writeTextBack(edited, probe);
    // Drawn again from the saved source, so what shows is what the section now holds.
    if (probe.innerHTML !== el.innerHTML) change((els) => writeTextBack(edited, els[at]), true);
  };

  /** Starts typing into element `at`, with the caret at the screen point, or all its text
   * selected without one. */
  const start = (at: number, point?: { x: number; y: number }) => {
    const edited = textNode(nodes.current[at]);
    if (!edited) return;
    typingRef.current = at;
    setTyping(at);
    edited.contentEditable = "true";
    edited.focus();
    placeCaret(edited, point);
  };

  useEffect(() => {
    if (typing === null) return;
    const onDown = (e: PointerEvent) => {
      const path = e.composedPath();
      const edited = textNode(nodes.current[typing]);
      if (edited && path.includes(edited)) return;
      if (path.some((n) => n instanceof HTMLElement && (n.dataset.formatBar !== undefined || n.closest("[role=dialog],[role=menu]")))) return;
      stop();
    };
    window.addEventListener("pointerdown", onDown, true);
    return () => window.removeEventListener("pointerdown", onDown, true);
  });

  /** Keys while typing stay in the text: the panel's own keys (arrows to change slide) must not
   * see them through the shadow root, where the text no longer looks like an editable target. */
  const onKey = (e: React.KeyboardEvent) => {
    if (typingRef.current === null) return;
    e.stopPropagation();
    if (e.key === "Escape") {
      e.preventDefault();
      stop();
    } else if (e.key === "Enter" && !e.shiftKey && !isList(typingRef.current)) {
      e.preventDefault();
      document.execCommand("insertLineBreak");
    }
  };
  const isList = (at: number) => ["ul", "ol"].includes(doc ? (elementsOf(doc)[at]?.localName ?? "") : "");

  /** Pasted text arrives as plain text: a slide's styles come from the slide, not the clipboard. */
  const onPaste = (e: React.ClipboardEvent) => {
    if (typingRef.current === null) return;
    e.preventDefault();
    document.execCommand("insertText", false, e.clipboardData.getData("text/plain"));
  };

  return { typing, start, stop, onKey, onPaste };
}

function placeCaret(edited: HTMLElement, point?: { x: number; y: number }) {
  const selection = (edited.getRootNode() as ShadowRoot & { getSelection?: () => Selection | null }).getSelection?.() ?? window.getSelection();
  if (!selection) return;
  const range = document.createRange();
  const caret = point && caretAt(edited, point);
  if (caret) {
    range.setStart(caret.offsetNode, caret.offset);
    range.collapse(true);
  } else range.selectNodeContents(edited);
  selection.removeAllRanges();
  selection.addRange(range);
}

type CaretFinder = (x: number, y: number, options?: { shadowRoots?: ShadowRoot[] }) => CaretPosition | null;

function caretAt(edited: HTMLElement, { x, y }: { x: number; y: number }) {
  const finder = (document as Document & { caretPositionFromPoint?: CaretFinder }).caretPositionFromPoint;
  if (!finder) return null;
  const root = edited.getRootNode();
  const found = finder.call(document, x, y, root instanceof ShadowRoot ? { shadowRoots: [root] } : undefined);
  return found && edited.contains(found.offsetNode) ? found : null;
}
