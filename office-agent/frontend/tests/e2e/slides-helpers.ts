import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, type Locator, type Page, type Request } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// Shared by the Slides specs that build a deck of section pages (HTML) in the server's workspace
// and open it in the Slides panel through the stub model, as slides.spec.ts does for SVG pages.
export const WORKSPACE = process.env.COSCRIBE_E2E_WORKSPACE;
const AGENT = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

export const threadOf = (page: Page) => new URL(page.url()).searchParams.get("thread") ?? "";
export const pageSource = (name: string, file: string) => readFileSync(join(WORKSPACE ?? "", `${name}-pages`, file), "utf-8");

export const freshDeckName = () => `deck-${Math.random().toString(36).slice(2, 8)}`;

/** Builds `name` from section pages and opens it expanded in the Slides panel. */
export async function openSectionDeck(page: Page, name: string) {
  execFileSync("python", [join("frontend", "tests", "e2e", "fixtures", "build_section_deck.py"), WORKSPACE ?? "", name], {
    cwd: AGENT,
    env: { ...process.env, PYTHONPATH: AGENT },
  });
  await page.goto(freshThreadPath("slides"));
  await waitForConnected(page);
  await page.locator("textarea").fill(`open it [[stub-tool read_pptx {"path":"${name}.pptx"}]]`);
  await page.keyboard.press("Enter");
  await page.getByTitle("Show task details").click();
  await page.getByRole("button", { name: `${name}.pptx Read` }).click();
  await page.getByRole("button", { name: "Expand Viewer" }).click();
  await expect(page.getByRole("button", { name: "Slide 1" }).first()).toBeVisible();
  trackSlideRequests(page);
}

const inflight = new WeakMap<Page, { open: Set<Request>; last: number }>();

/** Follows the Slides requests in flight, for `settled`. */
function trackSlideRequests(page: Page) {
  const state = { open: new Set<Request>(), last: Date.now() };
  inflight.set(page, state);
  const end = (r: Request) => {
    state.open.delete(r);
    state.last = Date.now();
  };
  page.on("request", (r) => r.url().includes("/slides") && state.open.add(r));
  page.on("requestfinished", end);
  page.on("requestfailed", end);
}

/** Waits for the editor to finish a change: its save, and the read of the slide that follows a
 * change the server lays out. Acting before then edits a copy the read is about to replace. */
export async function settled(page: Page) {
  const state = inflight.get(page);
  if (!state) return;
  await expect.poll(() => state.open.size === 0 && Date.now() - state.last > 400).toBe(true);
}

export interface Part {
  kind: string;
  box: number[] | null;
}

/** The slide as the server reads it back: the saved source and where each element is laid out. */
export async function partsOf(page: Page, name: string, index: number): Promise<{ name: string; source: string; parts: Part[] } | null> {
  const response = await page.request.get(`/api/threads/${threadOf(page)}/slides/${index}/parts?path=${name}.pptx`);
  // A read that lands while the server is rewriting the deck can fail for a moment; polling retries.
  return response.ok() ? response.json() : null;
}

/** Canvas px (1920 x 1080) to the page's, for the slide on screen. */
export async function slideAt(page: Page, x: number, y: number) {
  const layer = await page.getByLabel(/^(Edit the slide|Slide editor)$/).boundingBox();
  if (!layer) throw new Error("the slide is not on screen");
  const zoom = layer.width / 1920;
  return { x: layer.x + x * zoom, y: layer.y + y * zoom };
}

export async function clickSlide(page: Page, x: number, y: number, options: { dbl?: boolean } = {}) {
  const at = await slideAt(page, x, y);
  if (options.dbl) await page.mouse.dblclick(at.x, at.y);
  else await page.mouse.click(at.x, at.y);
}

export const goToSlide = (page: Page, n: number) => page.getByRole("button", { name: `Slide ${n}`, exact: true }).first().click();

export async function showProperties(page: Page): Promise<Locator> {
  const toggle = page.getByRole("button", { name: "Properties panel" });
  if ((await toggle.getAttribute("aria-pressed")) !== "true") await toggle.click();
  const panel = page.getByRole("complementary", { name: "Slide properties" });
  await expect(panel).toBeVisible();
  return panel;
}

/** Types into a number field of the properties panel and commits it with Enter. */
export async function setNumber(panel: Locator, label: string | RegExp, value: number) {
  const field = panel.getByRole("textbox", { name: label });
  await field.fill(String(value));
  await field.press("Enter");
  await settled(panel.page());
}

/** Picks a colour in the panel's colour field: the Custom tab, a hex value, Apply. */
export async function pickColour(page: Page, panel: Locator, field: string, hex: string) {
  await panel.getByRole("button", { name: field, exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Colour" });
  await dialog.getByRole("button", { name: "Custom" }).click();
  await dialog.getByLabel("Hex colour").fill(hex);
  await dialog.getByRole("button", { name: "Apply" }).click();
  await expect(dialog).toBeHidden();
  await settled(page);
}

/** What the saved source holds, read as XML in the page (Node has no DOMParser). `stack` is the
 * ids, or else the text, of the first container's children in order; `table` the first table's
 * rows and columns and how many of its cells are header cells. */
export function describeSource(page: Page, source: string) {
  return page.evaluate((text) => {
    const doc = new DOMParser().parseFromString(text, "text/xml");
    const stack = doc.querySelector("x-stack");
    const rows = Array.from(doc.querySelectorAll("table tr"));
    return {
      stack: stack ? Array.from(stack.children).map((c) => c.getAttribute("id") ?? c.textContent ?? "") : null,
      sectionChildren: Array.from(doc.documentElement.children).map((c) => c.getAttribute("id") ?? c.localName),
      table: { rows: rows.length, cols: rows[0]?.children.length ?? 0, headers: doc.querySelectorAll("table th").length },
      cells: rows.map((r) => Array.from(r.children).map((c) => c.textContent)),
    };
  }, source);
}

/** Drags with the mouse from one point of the slide to another. */
export async function dragOnSlide(page: Page, from: [number, number], to: [number, number]) {
  const a = await slideAt(page, ...from);
  const b = await slideAt(page, ...to);
  await page.mouse.move(a.x, a.y);
  await page.mouse.down();
  await page.mouse.move((a.x + b.x) / 2, (a.y + b.y) / 2, { steps: 4 });
  await page.mouse.move(b.x, b.y, { steps: 6 });
  await page.mouse.up();
}

/** Waits until `read` gives something, and returns it. */
export async function until<T>(read: () => Promise<T | null | undefined>): Promise<T> {
  let found: T | null | undefined;
  await expect
    .poll(async () => {
      found = await read();
      return found != null;
    })
    .toBe(true);
  return found as T;
}
