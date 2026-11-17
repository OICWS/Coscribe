/**
 * Taking data off a page: a table or list as rows, gathered across its
 * pages (a Next button) or as it loads more on scrolling, and the page as
 * a PDF. The rows and bytes go back to the server, which writes the file
 * where the person's folders allow.
 */

import type { WebContents } from "electron";
import type { Command } from "./browserAgent";
import type { PageActions } from "./browserAgentForms";
import { locate } from "./browserAgentLocate";
import type { TabCdp } from "./browserCdp";

interface Rows { kind: string; header: string[] | null; rows: string[][] }

const MAX_PAGES = 100;
const MAX_ROWS = 50_000;
// A missing Next button means the last page; a list that stops growing
// has nothing more to load. Neither should cost the whole step wait.
const NEXT_WAIT_S = 3;
const MORE_WAIT_S = 10;

/** Run in the page like pageAgent (browserAgentPage.ts), so self-contained.
 * Tables and lists carry no refs in a snapshot, so they are found by a text
 * they hold, which also finds them again after the page reloads. */
export function pageData(action: string, args: Record<string, unknown>): unknown {
  const TABLES = "table, [role=table], [role=grid], [role=treegrid]";
  const LISTS = "ul, ol, [role=list], [role=feed]";
  const clean = (text: string | null | undefined) => (text ?? "").replace(/\s+/g, " ").trim();
  const shown = (el: Element) => {
    const rect = el.getBoundingClientRect();
    return (rect.width > 0 || rect.height > 0) && getComputedStyle(el).visibility !== "hidden";
  };
  const rowsOf = (el: Element): Element[] => el instanceof HTMLTableElement
    ? Array.from(el.rows)
    : Array.from(el.querySelectorAll("[role=row]")).filter((row) => row.closest(TABLES) === el);
  const cellsOf = (row: Element): Element[] => row instanceof HTMLTableRowElement
    ? Array.from(row.cells)
    : Array.from(row.querySelectorAll("[role=cell], [role=gridcell], [role=columnheader], [role=rowheader]")).filter((c) => c.closest("[role=row]") === row);
  const itemsOf = (el: Element): Element[] => Array.from(el.children).filter((c) => !["SCRIPT", "TEMPLATE", "STYLE"].includes(c.tagName) && shown(c));

  const find = (): { el: Element; items: Element[] | null } => {
    const text = String(args.table ?? "").trim();
    const tables = Array.from(document.querySelectorAll(TABLES)).filter(shown);
    const lists = Array.from(document.querySelectorAll(LISTS)).filter((l) => shown(l) && itemsOf(l).length >= 2);
    if (!text) {
      const biggest = (els: Element[], size: (e: Element) => number) => els.reduce<Element | null>((best, e) => (!best || size(e) > size(best) ? e : best), null);
      const table = biggest(tables, (t) => rowsOf(t).length);
      if (table) return { el: table, items: null };
      const list = biggest(lists, (l) => itemsOf(l).length);
      if (list) return { el: list, items: itemsOf(list) };
      throw new Error("No table or list on this page -- name a text in the one you mean, like a column header.");
    }
    // The innermost holding the text: a layout table can hold the data table.
    const holding = [...tables, ...lists].filter((e) => (e as HTMLElement).innerText.includes(text));
    holding.sort((a, b) => (a as HTMLElement).innerText.length - (b as HTMLElement).innerText.length);
    if (holding[0]) return { el: holding[0], items: holding[0].matches(TABLES) ? null : itemsOf(holding[0]) };
    // Cards built from plain elements: the nearest ancestor that sits among
    // at least two more of its kind is one item, and its parent the list.
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (!node.textContent?.includes(text) || !node.parentElement || !shown(node.parentElement)) continue;
      for (let el: Element | null = node.parentElement; el?.parentElement && el !== document.body; el = el.parentElement) {
        const kin = itemsOf(el.parentElement).filter((s) => s.tagName === el!.tagName && s.className === el!.className);
        if (kin.length >= 3) return { el: el.parentElement, items: kin };
      }
    }
    throw new Error(`No table or list on this page holds "${text}".`);
  };

  const { el, items } = find();
  if (action === "scroll_more") {
    (items?.at(-1) ?? el).scrollIntoView({ block: "end", behavior: "instant" as ScrollBehavior });
    for (let box: Element | null = el; box; box = box.parentElement) {
      if (box.scrollHeight > box.clientHeight + 1 && /auto|scroll/.test(getComputedStyle(box).overflowY)) box.scrollTop = box.scrollHeight;
    }
    window.scrollTo(0, document.scrollingElement?.scrollHeight ?? 0);
    return {};
  }
  if (items) {
    const links = items.map((item) => (item instanceof HTMLAnchorElement ? item : item.querySelector<HTMLAnchorElement>("a[href]"))?.href ?? "");
    const rows = items.map((item, i) => {
      const lines = ((item as HTMLElement).innerText ?? "").split("\n").map(clean).filter(Boolean);
      return links.some(Boolean) ? [links[i], ...lines] : lines;
    }).filter((row) => row.some(Boolean));
    return { kind: "list", header: null, rows };
  }
  const grid: string[][] = [];
  const head: boolean[] = [];
  const rows = rowsOf(el).filter((row) => getComputedStyle(row).display !== "none");
  rows.forEach((row, r) => {
    grid[r] ??= [];
    let c = 0;
    const cells = cellsOf(row);
    for (const cell of cells) {
      while (grid[r][c] !== undefined) c++;
      const text = clean((cell as HTMLElement).innerText);
      const across = Math.min(Math.max(Number(cell.getAttribute("colspan")) || 1, 1), 100);
      const down = Math.min(Math.max(Number(cell.getAttribute("rowspan")) || 1, 1), rows.length - r);
      for (let dr = 0; dr < down; dr++) for (let dc = 0; dc < across; dc++) (grid[r + dr] ??= [])[c + dc] = text;
      c += across;
    }
    head[r] = row.parentElement?.tagName === "THEAD" || (cells.length > 0 && cells.every((cell) => cell.tagName === "TH" || cell.getAttribute("role") === "columnheader"));
  });
  const width = Math.max(0, ...grid.map((row) => row.length));
  const full = grid.map((row) => Array.from({ length: width }, (_, i) => row[i] ?? ""));
  let top = 0;
  while (top < full.length && head[top]) top++;
  const header = top
    ? Array.from({ length: width }, (_, i) => [...new Set(full.slice(0, top).map((row) => row[i]).filter(Boolean))].join(" / "))
    : null;
  return { kind: "table", header, rows: full.slice(top).filter((row) => row.some(Boolean)) };
}

/** The element as a description that finds it again after a reload, the
 * way the snapshot printed it: a Next button's ref is gone on page two. */
async function lasting(page: PageActions, cdp: TabCdp, target: string, waitS: number): Promise<string> {
  const ref = await page.resolveTarget(cdp, target, waitS);
  if (ref !== target.trim()) return target;
  const seen = new Map<string, number>();
  for (const line of (await page.snapshot(cdp)).lines) {
    const match = /^\s*- ([a-z]+)( ".*")? \[ref=((?:f\d+)?e\d+)\]/.exec(line);
    if (!match) continue;
    const base = `${match[1]}${match[2] ?? ""}`;
    seen.set(base, (seen.get(base) ?? 0) + 1);
    if (match[3] === ref) return seen.get(base) === 1 ? base : `${base} #${seen.get(base)}`;
  }
  return target;
}

async function changedRows(page: PageActions, read: () => Promise<Rows>, before: string, waitS: number): Promise<Rows | null> {
  const deadline = Date.now() + waitS * 1000;
  for (;;) {
    page.checkStop();
    // Mid-load the table may be gone for a moment.
    const rows = await read().catch(() => null);
    if (rows && JSON.stringify(rows.rows) !== before) return rows;
    if (Date.now() >= deadline) return null;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
}

async function collect(page: PageActions, wc: WebContents, cdp: TabCdp, args: Record<string, unknown>, waitS: number): Promise<Record<string, unknown>> {
  const read = () => cdp.agent<Rows>(cdp.main, "read", { table: args.table ?? "" }, pageData);
  const first = await read();
  const rows = [...first.rows];
  const seen = new Set(rows.map((row) => JSON.stringify(row)));
  const header = JSON.stringify(first.header);
  const maxPages = Math.min(Math.max(Number(args.max_pages) || 1, 1), MAX_PAGES);
  const next = args.next_page ? await lasting(page, cdp, String(args.next_page), waitS) : "";
  let last = JSON.stringify(first.rows);
  let pages = 1;
  let stopped = "end";
  while (next || args.scroll) {
    if (pages >= maxPages) { stopped = "max_pages"; break; }
    if (rows.length >= MAX_ROWS) { stopped = "rows"; break; }
    page.checkStop();
    if (next) {
      const ref = await page.resolveTarget(cdp, next, Math.min(waitS, NEXT_WAIT_S)).catch(() => "");
      if (!ref) break;
      const line = (await page.snapshot(cdp)).lines.find((l) => l.includes(`[ref=${ref}]`)) ?? "";
      if (line.includes("[disabled]")) break;
      await page.click(wc, cdp, await locate(cdp, ref), 1);
    } else {
      await cdp.agent(cdp.main, "scroll_more", { table: args.table ?? "" }, pageData);
    }
    await page.settle(wc);
    const fresh = await changedRows(page, read, last, next ? waitS : Math.min(waitS, MORE_WAIT_S));
    if (!fresh) break;
    last = JSON.stringify(fresh.rows);
    pages++;
    for (const row of fresh.rows) {
      const key = JSON.stringify(row);
      // A list that loads more on scrolling may still show what was read;
      // a table repeats its header row on every page.
      if ((args.scroll && seen.has(key)) || key === header) continue;
      seen.add(key);
      rows.push(row);
    }
  }
  return { kind: first.kind, header: first.header, rows: rows.slice(0, MAX_ROWS), pages, stopped };
}

export async function runData(page: PageActions, command: Command, wc: WebContents, cdp: TabCdp, args: Record<string, unknown>, waitS: number): Promise<Record<string, unknown>> {
  if (command.action === "save_pdf") {
    const pdf = await wc.printToPDF({ printBackground: true, landscape: args.landscape === true });
    return { pdf: pdf.toString("base64") };
  }
  return collect(page, wc, cdp, args, waitS);
}
