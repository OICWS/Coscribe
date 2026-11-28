import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// A reply that names a file the conversation made shows a chip with a hover card, and the end of the
// turn a card that opens it (the stub model writes the Doc, then says its name).
test.skip(!process.env.COSCRIBE_E2E_WORKSPACE, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({ viewport: { width: 1600, height: 1000 } });

// A name in Chinese is percent-encoded by the markdown pipeline on its way to the chip.
for (const prefix of ["made", "AI新闻月报"]) {
test(`a file named in a reply is a chip with a card on hover, and the turn ends with a card that opens it (${prefix})`, async ({ page }) => {
  const name = `${prefix}-${Math.random().toString(36).slice(2, 8)}`;
  await page.goto(freshThreadPath("chat-files"));
  await waitForConnected(page);
  await page.locator("textarea").fill(`write it [[stub-tool write_file {"path":"${name}.md","content":"---\\ncoscribe: doc\\n---\\n\\n# Title\\n\\nBody"}]] [[stub-say I wrote ${name}.md for you.]]`);
  await page.keyboard.press("Enter");

  const chip = page.locator("p").getByRole("button", { name });
  await expect(chip).toBeVisible();
  await chip.hover();
  const card = page.getByRole("tooltip").filter({ hasText: "Document" });
  await expect(card).toContainText("Document");
  await expect(card).toContainText(name);

  // The chip opens the file too, not a file named by its encoded address.
  await page.mouse.move(5, 500);
  await chip.click();
  await expect(page.getByRole("region", { name: "Viewer" })).toBeVisible();

  // The notice above the message box opens the same file under the same title; the end card is the one with its kind.
  const end = page.getByTitle(`Open ${name}.md`).filter({ hasText: "Document · .md" });
  await expect(end).toBeVisible();
  await expect(end).toContainText("Document · .md");
  await page.mouse.move(5, 500);
  await end.click();
  await expect(page.getByRole("region", { name: "Viewer" })).toBeVisible();
});
}

test("a Word file card opens the preview and its menu opens the original in Word", async ({ page }) => {
  const name = `word-${Math.random().toString(36).slice(2, 8)}`;
  const opened: string[] = [];
  const pdf = readFileSync(new URL("./fixtures/sample.pdf", import.meta.url));
  await page.route("**/api/attachment/docx?*", (route) => route.fulfill({
    body: pdf, contentType: "application/pdf",
  }));
  await page.route("**/files/open", async (route) => {
    opened.push(route.request().postData() ?? "");
    await route.fulfill({ json: { ok: true } });
  });
  await page.goto(freshThreadPath("chat-files-word"));
  await waitForConnected(page);
  await page.locator("textarea").fill(`write it [[stub-tool write_docx {"path":"${name}.docx","content":"# Title\\n\\nBody"}]] [[stub-say I wrote ${name}.docx for you.]]`);
  await page.keyboard.press("Enter");

  const card = page.getByTitle(`Open ${name}.docx`);
  await expect(card).toBeVisible();
  const viewer = page.getByRole("region", { name: "Viewer" });
  await expect(viewer).toHaveCount(0);
  await card.click();
  await expect(viewer.getByText("Page 1 of 2", { exact: true })).toBeVisible();
  expect(opened).toHaveLength(0);
  await page.getByRole("button", { name: `File options for ${name}.docx` }).click();
  await page.getByRole("menuitem", { name: "Open in Word" }).click();
  await expect.poll(() => opened.length).toBe(1);
  expect(JSON.parse(opened[0])).toEqual({ path: `${name}.docx`, reveal: false });
});

test("a Markdown file that is not a Doc gets no card that leads nowhere", async ({ page }) => {
  const name = `notes-${Math.random().toString(36).slice(2, 8)}`;
  await page.goto(freshThreadPath("chat-files-notes"));
  await waitForConnected(page);
  await page.locator("textarea").fill(`write it [[stub-tool write_file {"path":"${name}.md","content":"# Notes\\n\\nJust notes."}]] [[stub-say I wrote ${name}.md for you.]]`);
  await page.keyboard.press("Enter");
  await expect(page.getByText(`I wrote ${name}.md for you.`, { exact: true })).toBeVisible();

  // The lookups have long answered by now; no chip, no card.
  await page.waitForTimeout(1500);
  await expect(page.getByTitle(`Open ${name}.md`)).toHaveCount(0);
  await expect(page.locator("p").getByRole("button", { name })).toHaveCount(0);
});
