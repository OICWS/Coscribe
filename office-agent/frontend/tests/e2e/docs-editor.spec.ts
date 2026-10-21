import { execFileSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// The Docs editor against the real server (decision 0019): what is typed reaches the .docx, and what
// the editor does not model (the comment, the tracked changes) is still in the file afterwards. Each
// step checks the blocks and the review the server reads back, not only the screen.
const WORKSPACE = process.env.COSCRIBE_E2E_WORKSPACE;
const AGENT = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

test.skip(!WORKSPACE, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({ viewport: { width: 1600, height: 1200 } });

interface Blocks {
  version: string;
  blocks: { kind: string; what?: string; runs?: { t: string; b?: boolean }[] }[];
}

const threadOf = (page: Page) => new URL(page.url()).searchParams.get("thread") ?? "";
const textOf = (block: Blocks["blocks"][number]) => (block.runs ?? []).map((r) => r.t).join("");

async function openEditor(page: Page, name: string) {
  execFileSync("python", [join("frontend", "tests", "e2e", "fixtures", "build_redline.py"), WORKSPACE ?? "", name], {
    cwd: AGENT,
    env: { ...process.env, PYTHONPATH: AGENT },
  });
  await page.goto(freshThreadPath("docs-editor"));
  await waitForConnected(page);
  await page.locator("textarea").fill(`open it [[stub-tool read_docx {"path":"${name}.docx"}]]`);
  await page.keyboard.press("Enter");
  await page.getByTitle("Show task details").click();
  await page.getByRole("button", { name: `${name}.docx Read` }).click();
  await page.getByRole("button", { name: "Expand Viewer" }).click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await expect(page.locator(".docs-editor")).toBeVisible();
  // A click in the first moments after the editor appears sometimes lands the caret at the start of
  // the document (seen 2 runs in 8, never after half a second); the cause is not found yet (#507).
  await page.waitForTimeout(500);
}

const blocksOf = async (page: Page, name: string): Promise<Blocks> => {
  const response = await page.request.get(`/api/threads/${threadOf(page)}/docs/blocks?path=${name}.docx`);
  expect(response.ok()).toBe(true);
  return response.json();
};

test("an edit in the editor reaches the Word file and leaves its comment and changes alone", async ({ page }) => {
  const name = `edit-${Math.random().toString(36).slice(2, 8)}`;
  await openEditor(page, name);
  const editor = page.locator(".docs-editor");
  await expect(editor.locator(".docs-title")).toHaveText("Service agreement");
  await expect(editor.locator(".docs-locked")).toHaveCount(1); // the price line, which holds the comment and both changes

  await test.step("typing in a paragraph is saved to the file", async () => {
    const term = editor.locator("p", { hasText: "The agreement runs" });
    await term.click();
    await page.keyboard.press("End");
    await page.keyboard.type(" Renewal is by letter.");
    await expect(page.getByRole("status")).toHaveText("Saved");
    const saved = (await blocksOf(page, name)).blocks;
    expect(saved.map(textOf).some((t) => t.includes("Renewal is by letter."))).toBe(true);
  });

  await test.step("bold, a new heading and a list are written as styles", async () => {
    await editor.locator(".docs-title").click();
    await page.keyboard.press("End");
    await page.keyboard.press("Enter");
    await page.getByTitle("Paragraph style").click();
    await page.getByRole("menuitemradio", { name: "Heading 2" }).click();
    await page.keyboard.type("Notes");
    await page.keyboard.press("Enter");
    await page.getByRole("button", { name: "Bulleted list" }).click();
    await page.keyboard.type("first point");
    await expect(page.getByRole("status")).toHaveText("Saved");
    const kinds = (await blocksOf(page, name)).blocks.map((b) => `${b.kind}:${textOf(b)}`);
    expect(kinds).toContain("heading:Notes");
    expect(kinds).toContain("bullet:first point");
  });

  await test.step("the comment and the tracked changes are still in the file", async () => {
    const review = await (await page.request.get(`/api/threads/${threadOf(page)}/docx-review?path=${name}.docx`)).json();
    expect(review.comments).toHaveLength(1);
    expect(review.changes.map((c: { kind: string }) => c.kind).sort()).toEqual(["delete", "insert"]);
  });

  await test.step("the Word layout shows what was written", async () => {
    await page.getByRole("button", { name: "Word layout" }).click();
    await expect(page.locator(".docx-page")).toContainText("Renewal is by letter.");
  });
});

test("a file changed meanwhile is not overwritten: the editor says so and reads it again", async ({ page }) => {
  const name = `edit-${Math.random().toString(36).slice(2, 8)}`;
  await openEditor(page, name);
  const editor = page.locator(".docs-editor");
  const read = await blocksOf(page, name);
  // Someone saves a change behind the editor's back: the version it holds is now stale.
  const changed = read.blocks.map((b) => (b.runs?.[0]?.t === "The agreement runs for one year." ? { ...b, runs: [{ t: "Changed elsewhere." }] } : b));
  const behind = await page.request.put(`/api/threads/${threadOf(page)}/docs/blocks`, { data: { path: `${name}.docx`, version: read.version, blocks: changed } });
  expect(behind.ok()).toBe(true);

  await editor.locator("p", { hasText: "The agreement runs" }).click();
  await page.keyboard.type("!");
  await expect(page.getByText("This document changed since you opened it")).toBeVisible();
  await page.getByRole("button", { name: "Reload" }).click();
  await expect(editor).toContainText("Changed elsewhere.");
  await expect(page.getByText("This document changed since you opened it")).toHaveCount(0);
  expect((await blocksOf(page, name)).blocks.map(textOf).join("\n")).not.toContain("!");
});

test("'/' inserts a block and the bar over selected words formats them, both written to the file", async ({ page }) => {
  const name = `edit-${Math.random().toString(36).slice(2, 8)}`;
  await openEditor(page, name);
  const editor = page.locator(".docs-editor");

  await test.step("'/' narrows as it is typed and Enter makes a heading", async () => {
    await editor.locator("p", { hasText: "The agreement runs" }).click();
    await page.keyboard.press("End");
    await page.keyboard.press("Enter");
    await page.keyboard.type("/head");
    await expect(page.getByRole("option")).toHaveText([/Heading 1/, /Heading 2/, /Heading 3/]);
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");
    await page.keyboard.type("Appendix");
    await expect(page.getByRole("status")).toHaveText("Saved");
    expect((await blocksOf(page, name)).blocks.map((b) => `${b.kind}:${textOf(b)}`)).toContain("heading:Appendix");
  });

  await test.step("a table comes from '/' too, and a table's cells take no menu", async () => {
    await page.keyboard.press("Enter");
    await page.keyboard.type("/table");
    await page.getByRole("option", { name: /Table/ }).click();
    await expect(editor.locator("table")).toHaveCount(1);
    await editor.locator("td").first().click();
    await page.keyboard.type("/");
    await expect(page.getByRole("option")).toHaveCount(0);
  });

  await test.step("selected words get a bar: bold is written to the file", async () => {
    await editor.locator("p", { hasText: "The agreement runs" }).click({ clickCount: 3 });
    const bar = page.getByRole("toolbar", { name: "Format selected text" });
    await expect(bar).toBeVisible();
    await bar.getByRole("button", { name: "Bold" }).click();
    await expect(page.getByRole("status")).toHaveText("Saved");
    const term = (await blocksOf(page, name)).blocks.find((b) => textOf(b).startsWith("The agreement runs"));
    expect(term?.runs?.every((r) => r.b)).toBe(true);
  });
});

test("a turn that ends does not rebuild the editor or move the caret", async ({ page }) => {
  const name = `edit-${Math.random().toString(36).slice(2, 8)}`;
  await openEditor(page, name);
  const editor = page.locator(".docs-editor");
  await editor.evaluate((el) => el.setAttribute("data-same-editor", "yes"));
  await editor.locator("p", { hasText: "The agreement runs" }).click();
  await page.keyboard.press("End");

  await page.getByRole("button", { name: "Restore Viewer" }).click();
  await page.locator("textarea").fill("hello again");
  await page.keyboard.press("Enter");
  await expect(page.getByText("OK", { exact: true })).toBeVisible();
  await page.waitForTimeout(1500);

  await expect(editor).toHaveAttribute("data-same-editor", "yes");
  await editor.locator("p", { hasText: "The agreement runs" }).click();
  await page.keyboard.press("End");
  await page.keyboard.type(" Kept.");
  await expect(page.getByRole("status")).toHaveText("Saved");
  expect((await blocksOf(page, name)).blocks.map(textOf).some((t) => t.includes("The agreement runs for one year. Kept."))).toBe(true);
});
