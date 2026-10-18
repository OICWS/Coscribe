import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// The Slides panel against the real server: every step checks the files on disk or the slides
// API, not only what the screen shows. The deck is built into the server's workspace by
// fixtures/build_deck.py, and the stub model "reads" it so it appears among the thread's files.
const WORKSPACE = process.env.COSCRIBE_E2E_WORKSPACE;
const AGENT = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

test.skip(!WORKSPACE, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({ viewport: { width: 1600, height: 1200 } });

interface Slide {
  name: string;
  elements: { id: string; label: string; box: number[] }[];
}

const pages = (name: string) => join(WORKSPACE ?? "", `${name}-pages`);
const sources = (name: string) => readdirSync(pages(name)).filter((f) => /\.(svg|html)$/.test(f)).sort();
const threadOf = (page: Page) => new URL(page.url()).searchParams.get("thread") ?? "";

async function openDeck(page: Page, name: string) {
  execFileSync("python", [join("frontend", "tests", "e2e", "fixtures", "build_deck.py"), WORKSPACE ?? "", name], {
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
}

const api = async (page: Page, path: string) => {
  const response = await page.request.get(`/api/threads/${threadOf(page)}${path}`);
  expect(response.ok(), path).toBe(true);
  return response.json();
};
const deckOf = (page: Page, name: string): Promise<{ slides: Slide[]; changed: boolean }> =>
  api(page, `/slides?path=${name}.pptx`);

test("the Slides panel: view, comment, edit, arrange and undo, each checked on the server", async ({ page }) => {
  const name = `deck-${Math.random().toString(36).slice(2, 8)}`;
  await openDeck(page, name);

  await test.step("the slides and their thumbnails show", async () => {
    const deck = await deckOf(page, name);
    expect(deck.slides.map((s) => s.name)).toEqual(["01-cover.svg", "02-cards.svg"]);
    expect(sources(name)).toEqual(["01-cover.svg", "02-cards.svg"]);
    for (const n of [1, 2]) {
      const thumb = page.getByRole("button", { name: `Slide ${n}`, exact: true }).first().locator("img");
      await expect(thumb).toBeVisible();
      await expect.poll(() => thumb.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
    }
  });

  await test.step("a comment is added and kept in the deck's comments", async () => {
    await page.getByRole("button", { name: "Comment", exact: true }).click();
    await page.getByLabel("Click to comment").click({ position: { x: 300, y: 200 } });
    await page.getByRole("textbox", { name: "Comment" }).fill("Check the title");
    await page.getByRole("button", { name: "Post comment" }).click();
    await expect.poll(async () => (await api(page, `/slides/comments?path=${name}.pptx`)).length).toBe(1);
    const [comment] = await api(page, `/slides/comments?path=${name}.pptx`);
    expect(comment).toMatchObject({ text: "Check the title", slide: "01-cover", resolved: false });
    expect(JSON.parse(readFileSync(join(pages(name), "comments.json"), "utf-8")).comments).toHaveLength(1);
    await page.getByRole("button", { name: "Comment", exact: true }).click();
  });

  const slideAt = async (x: number, y: number) => {
    const layer = await page.getByLabel(/^(Edit the slide|Slide editor)$/).boundingBox();
    if (!layer) throw new Error("the slide is not on screen");
    const zoom = layer.width / 1920;
    return { x: layer.x + x * zoom, y: layer.y + y * zoom };
  };
  const source = (file: string) => readFileSync(join(pages(name), file), "utf-8");

  await test.step("a click starts editing", async () => {
    const title = await slideAt(162 + 300, 455 + 70);
    await page.mouse.click(title.x, title.y);
    await expect(page.getByLabel("Slide editor")).toBeVisible();
    // The editor loads the page before it can select what was clicked.
    await expect(page.getByLabel("Text style")).toBeVisible();
  });

  await test.step("dragging an element saves the page as HTML", async () => {
    const [x, y] = [162 + 300, 455 + 70];
    const from = await slideAt(x, y);
    const to = await slideAt(x + 160, y + 100);
    await page.mouse.move(from.x, from.y);
    await page.mouse.down();
    await page.mouse.move((from.x + to.x) / 2, (from.y + to.y) / 2, { steps: 4 });
    await page.mouse.move(to.x, to.y, { steps: 4 });
    await page.mouse.up();
    await expect.poll(() => sources(name)).toEqual(["01-cover.html", "02-cards.svg"]);
    const parsed = await api(page, `/slides/0/parts?path=${name}.pptx`);
    expect(parsed.name).toBe("01-cover.html");
    const [, left] = /id="title" style="left:([\d.]+)px/.exec(source("01-cover.html")) ?? [];
    expect(Number(left)).toBeGreaterThan(162.12 + 100);
  });

  await test.step("a text box is inserted and typed into", async () => {
    await page.getByRole("button", { name: "Add a text box" }).click();
    await page.keyboard.type("Hello from the e2e");
    const empty = await slideAt(1700, 1000);
    await page.mouse.click(empty.x, empty.y);
    await expect.poll(() => source("01-cover.html")).toContain("Hello from the e2e");
    const parsed = await api(page, `/slides/0/parts?path=${name}.pptx`);
    expect(parsed.parts).toHaveLength(4);
  });

  const slideNames = async () => {
    const response = await page.request.get(`/api/threads/${threadOf(page)}/slides?path=${name}.pptx`);
    return response.ok() ? ((await response.json()).slides as Slide[]).map((slide) => slide.name) : [];
  };
  const stems = (names: string[]) => names.map((n) => n.replace(/^\d+-/, "").replace(/\.(svg|html)$/, ""));
  const thumbnail = (n: number) => page.getByRole("button", { name: `Slide ${n}`, exact: true }).last();
  const menuItem = (label: string) => page.getByRole("menuitem", { name: new RegExp(`^${label}`) });

  await test.step("a new slide from the New slide dialog", async () => {
    await page.getByRole("button", { name: "New slide", exact: true }).click();
    await page.getByRole("dialog", { name: "New slide" }).getByText("Title", { exact: true }).click();
    await expect.poll(async () => (await slideNames()).length).toBe(3);
    const names = await slideNames();
    expect(sources(name)).toEqual(names);
    expect(names.every((n, i) => n.startsWith(`${String(i + 1).padStart(2, "0")}-`))).toBe(true);
    expect(names.filter((n) => n.endsWith(".html"))).toHaveLength(2);
  });

  await test.step("a slide is duplicated, moved and deleted from the thumbnails", async () => {
    await thumbnail(1).click({ button: "right", position: { x: 20, y: 5 } });
    await menuItem("Duplicate").click();
    await expect.poll(async () => (await slideNames()).length).toBe(4);
    const copied = stems(await slideNames());
    expect(copied).toEqual(["cover", "cover-copy", "slide", "cards"]);
    expect(sources(name)).toEqual(await slideNames());

    await thumbnail(1).dragTo(thumbnail(4));
    await expect.poll(async () => stems(await slideNames())).toEqual(["cover-copy", "slide", "cards", "cover"]);
    expect(sources(name)).toEqual(await slideNames());

    await thumbnail(2).click({ button: "right", position: { x: 20, y: 5 } });
    await menuItem("Delete").click();
    await expect.poll(async () => stems(await slideNames())).toEqual(["cover-copy", "cards", "cover"]);
    expect(sources(name)).toEqual(await slideNames());
  });

  await test.step("Undo and Redo from the zoom menu", async () => {
    const deleted = await slideNames();
    const zoomMenu = page.getByRole("button", { name: /^Zoom \d+%/ });
    await zoomMenu.click();
    await menuItem("Undo").click();
    await expect.poll(async () => (await slideNames()).length).toBe(4);
    expect(sources(name)).toEqual(await slideNames());
    await zoomMenu.click();
    await menuItem("Redo").click();
    await expect.poll(slideNames).toEqual(deleted);
    expect(sources(name)).toEqual(deleted);
  });
});
