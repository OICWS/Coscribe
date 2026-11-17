/**
 * Seeing a page as a picture, for what has no element to name (a canvas,
 * a chart, an icon without a label), and reading the text around a label,
 * for a value a run compares with the last one.
 */

import type { WebContents } from "electron";
import type { PageActions } from "./browserAgentForms";
import type { TabCdp } from "./browserCdp";

// What a vision model reads at full detail; wider pages are scaled down.
const LOOK_WIDTH = 1280;
const TEXT_CHARS = 2_000;
const PAGE_CHARS = 20_000;

/** Run in the page like pageAgent (browserAgentPage.ts), so self-contained. */
export function pageText(action: string, args: Record<string, unknown>): unknown {
  const clean = (text: string) => text.replace(/[ \t ]+/g, " ").replace(/\s*\n\s*/g, "\n").trim();
  if (action === "viewport") return { width: window.innerWidth, height: window.innerHeight };
  const near = String(args.near ?? "").trim();
  if (!near) return { text: clean(document.body?.innerText ?? "").slice(0, Number(args.page_chars)) };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const parent = node.parentElement;
    if (!parent || !node.textContent?.includes(near) || !(parent.getClientRects().length > 0)) continue;
    // The block the label sits in, or the one around it when the label is a block of its own
    // (a <dt>, a heading above the value): the value is what is next to it.
    let el: HTMLElement = parent;
    while (el.parentElement && el.parentElement !== document.body
      && (getComputedStyle(el).display.startsWith("inline") || clean(el.innerText) === near)) {
      el = el.parentElement;
    }
    return { text: clean(el.innerText).slice(0, Number(args.chars)) };
  }
  return { text: null };
}

/** The visible part of the page as a PNG, with how many page pixels one
 * picture pixel is, which a later click by position scales back by. */
export async function look(page: PageActions, wc: WebContents, cdp: TabCdp): Promise<Record<string, unknown>> {
  await page.settle(wc);
  const { width, height } = await cdp.agent<{ width: number; height: number }>(cdp.main, "viewport", {}, pageText);
  let image = await wc.capturePage();
  const wide = Math.min(width, LOOK_WIDTH);
  if (image.getSize().width !== wide) image = image.resize({ width: wide });
  cdp.lookScale = width / image.getSize().width;
  return { png: image.toPNG().toString("base64"), width: image.getSize().width, height: image.getSize().height };
}

/** The text around `near` (or the whole page's), once it is there. */
export async function readText(page: PageActions, cdp: TabCdp, args: Record<string, unknown>, waitS: number): Promise<Record<string, unknown>> {
  const deadline = Date.now() + waitS * 1000;
  for (;;) {
    page.checkStop();
    const { text } = await cdp
      .agent<{ text: string | null }>(cdp.main, "read", { near: args.near ?? "", chars: TEXT_CHARS, page_chars: PAGE_CHARS }, pageText)
      .catch(() => ({ text: null }));
    if (text !== null) return { text };
    if (cdp.dialog) throw new Error(page.describeDialog(cdp.dialog));
    if (Date.now() >= deadline) throw new Error(`"${args.near}" didn't appear on the page within ${waitS}s.`);
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
}
