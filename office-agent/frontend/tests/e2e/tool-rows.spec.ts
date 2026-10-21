import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// An opened tool call reads as "name: value" lines; the JSON is only behind "Raw".
test("an opened tool call shows plain lines, and its JSON only behind Raw", async ({ page }) => {
  await page.goto(freshThreadPath("tool-rows"));
  await waitForConnected(page);
  await page.locator("textarea").fill('list them [[stub-tool list_files {"path":".","pattern":"*.md"}]]');
  await page.keyboard.press("Enter");

  const header = page.getByRole("button", { name: /Listed files/ });
  await header.click();

  await expect(page.getByText("pattern:", { exact: true })).toBeVisible();
  await expect(page.getByText("*.md", { exact: true })).toBeVisible();
  const raw = page.locator("details pre");
  await expect(raw).toBeHidden();

  await page.getByText("Raw", { exact: true }).click();
  await expect(raw).toContainText('"pattern": "*.md"');
});
