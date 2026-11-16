/**
 * Moving things on a page: dragging, dropping files, and copying and
 * pasting through the AI's own clipboard.
 *
 * Dragging uses real input: a mouse press, moves and a release, which is
 * all a slider or a mouse-driven list needs. A page using HTML5 drag and
 * drop starts a native drag instead, which protocol mouse events can't
 * carry to a drop target; with drags intercepted, Chromium hands over that
 * drag's data and the drop is sent as drag events at the target.
 */

import type { WebContents } from "electron";
import type { Command } from "./browserAgent";
import type { PageActions } from "./browserAgentForms";
import { locate, splitRef } from "./browserAgentLocate";
import type { TabCdp } from "./browserCdp";

type Point = { x: number; y: number };

const MOVE_STEPS = 12;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function dropAt(cdp: TabCdp, to: Point, data: unknown): Promise<void> {
  for (const type of ["dragEnter", "dragOver", "drop"]) {
    await cdp.input("Input.dispatchDragEvent", { type, x: to.x, y: to.y, data });
  }
}

/** "html5" when the page dragged natively, "mouse" when the moves did it. */
export async function dragBetween(cdp: TabCdp, from: Point, to: Point): Promise<"html5" | "mouse"> {
  await cdp.send("Input.setInterceptDrags", { enabled: true });
  cdp.dragData = null;
  let kind: "html5" | "mouse" = "mouse";
  try {
    await cdp.input("Input.dispatchMouseEvent", { type: "mouseMoved", x: from.x, y: from.y });
    await cdp.input("Input.dispatchMouseEvent", { type: "mousePressed", x: from.x, y: from.y, button: "left", buttons: 1, clickCount: 1 });
    // Pages start a drag only past a few pixels, and many track every move.
    // Sent without waiting for each: a page off screen acknowledges input
    // only with its next frame, about a second apart, and the protocol keeps
    // their order anyway.
    const moves: Promise<void>[] = [];
    for (let n = 1; n <= MOVE_STEPS; n++) {
      const x = from.x + ((to.x - from.x) * n) / MOVE_STEPS;
      const y = from.y + ((to.y - from.y) * n) / MOVE_STEPS;
      moves.push(cdp.input("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "left", buttons: 1 }));
    }
    await Promise.all(moves);
    await sleep(50);
    if (cdp.dragData) {
      kind = "html5";
      await dropAt(cdp, to, cdp.dragData);
    }
    await cdp.input("Input.dispatchMouseEvent", { type: "mouseReleased", x: to.x, y: to.y, button: "left", buttons: 0, clickCount: 1 });
  } finally {
    cdp.dragData = null;
    await cdp.send("Input.setInterceptDrags", { enabled: false }).catch(() => undefined);
  }
  return kind;
}

/** Files dropped from outside the page, as a person drags them in from a folder. */
export async function dropOnto(cdp: TabCdp, ref: unknown, files: string[]): Promise<string> {
  if (!ref) throw new Error("Pass the ref of the area to drop the files on.");
  const point = await locate(cdp, ref);
  // 1 is "copy", what a file manager offers.
  await dropAt(cdp, point, { items: [], files, dragOperationsMask: 1 });
  return point.element;
}

/** The AI's clipboard, one per conversation or run. The person's own
 * clipboard is never read or written: it may hold their passwords, and a
 * copy by the AI would replace what they copied (the maintainer's choice). */
const clipboards = new Map<string, { text: string; html: string }>();
const CLIPBOARD_CHARS = 1_000_000;

/** Run in the page like pageAgent, so self-contained; reaches pageAgent's
 * elements through the refs it left on window. */
export function pageClipboard(action: string, args: Record<string, unknown>): unknown {
  const w = window as unknown as { __coscribeAgent?: { refs: Map<string, WeakRef<Element>> } };
  const el = args.ref ? w.__coscribeAgent?.refs.get(String(args.ref))?.deref() : undefined;
  if (args.ref && !el?.isConnected) throw new Error(`No element with ref ${args.ref} on this page any more -- take a new browser_snapshot.`);
  if (action === "copy") {
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement) {
      return { text: el.value, html: "" };
    }
    if (el) return { text: (el as HTMLElement).innerText ?? el.textContent ?? "", html: el.outerHTML };
    const selection = getSelection();
    if (!selection || selection.isCollapsed) throw new Error("Nothing is selected on the page -- pass the ref of what to copy.");
    const box = document.createElement("div");
    for (let i = 0; i < selection.rangeCount; i++) box.append(selection.getRangeAt(i).cloneContents());
    return { text: selection.toString(), html: box.innerHTML };
  }
  // "paste_html": into the focused rich-text editor, where typed text would lose its formatting.
  const target = document.activeElement as HTMLElement | null;
  if (!target?.isContentEditable) return { rich: false };
  return { rich: document.execCommand("insertHTML", false, String(args.html)) };
}

/** drag, copy and paste; null for any other action. */
export async function runMove(page: PageActions, command: Command, wc: WebContents, cdp: TabCdp, args: Record<string, unknown>, waitS: number): Promise<Record<string, unknown> | null> {
  if (command.action === "drag") {
    const from = await locate(cdp, args.ref);
    let to = { x: from.x + Number(args.by_x || 0), y: from.y + Number(args.by_y || 0) };
    let onto = "";
    if (args.target) {
      const point = await locate(cdp, await page.resolveTarget(cdp, String(args.target), waitS));
      to = point;
      onto = point.element;
    }
    const how = await dragBetween(cdp, from, to);
    await page.settle(wc);
    return { element: from.element, onto, how };
  }
  if (command.action === "copy") {
    const { key, inner } = splitRef(args.ref);
    const copied = await cdp.agent<{ text: string; html: string }>(cdp.frame(key), "copy", { ref: args.ref ? inner : "" }, pageClipboard);
    if (copied.text.length > CLIPBOARD_CHARS) throw new Error(`That is ${copied.text.length} characters; copy a smaller part (at most ${CLIPBOARD_CHARS}).`);
    clipboards.set(command.thread_id, copied);
    return { chars: copied.text.length, preview: copied.text.slice(0, 200) };
  }
  if (command.action === "paste") {
    const copied = clipboards.get(command.thread_id);
    if (!copied) throw new Error("Nothing has been copied yet -- copy with browser_copy first.");
    const point = await locate(cdp, args.ref);
    await page.click(wc, cdp, point, 1);
    const { rich } = copied.html && args.plain !== true
      ? await cdp.agent<{ rich: boolean }>(point.frame, "paste_html", { html: copied.html }, pageClipboard)
      : { rich: false };
    if (!rich) {
      await cdp.agent(point.frame, "select_all_in_focus");
      await cdp.input("Input.insertText", { text: copied.text });
    }
    await page.settle(wc);
    return { element: point.element, chars: copied.text.length, formatted: rich };
  }
  return null;
}
