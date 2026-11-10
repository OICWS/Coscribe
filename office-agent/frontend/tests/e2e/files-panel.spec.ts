import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

const workspace = process.env.COSCRIBE_E2E_WORKSPACE ?? "";
test.skip(!workspace, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({ viewport: { width: 1440, height: 900 } });

test("the Files panel finds a file by name, draws markdown and pages, and shows code as highlighted source", async ({ page }) => {
  const id = Math.random().toString(36).slice(2, 8);
  const folder = join(workspace, `files-${id}`);
  mkdirSync(folder, { recursive: true });
  writeFileSync(join(folder, `notes-${id}.md`), "# Weekly notes\n\nAll **done**.\n");
  writeFileSync(join(folder, `tool-${id}.py`), "def hello():\n    return 1\n");
  writeFileSync(join(folder, `page-${id}.html`), "<h1>Hello page</h1><script>document.body.textContent = 'SCRIPT RAN'</script>");

  await page.goto(freshThreadPath("files"));
  await waitForConnected(page);
  await page.locator("textarea").fill("Reply with just the word ok.");
  await page.keyboard.press("Enter");
  await page.getByTitle("Files", { exact: true }).click();
  const panel = page.getByRole("region", { name: "Files", exact: true });

  const filter = panel.getByLabel("Filter files");
  await filter.fill(`notes-${id}`);
  await panel.getByRole("button", { name: new RegExp(`notes-${id}\\.md`) }).click();
  await expect(panel.getByRole("heading", { name: "Weekly notes" })).toBeVisible();
  await panel.getByTitle("View source").click();
  await expect(panel.getByTestId("code-view")).toContainText("# Weekly notes");
  await expect(panel.getByRole("tab", { name: `notes-${id}.md` })).toBeVisible();

  await filter.fill(`tool-${id}`);
  await panel.getByRole("button", { name: new RegExp(`tool-${id}\\.py`) }).click();
  await expect(panel.getByTestId("code-view")).toContainText("def hello():");
  // The preview tab is replaced by the next file opened.
  await expect(panel.getByRole("tab")).toHaveCount(1);

  await filter.fill(`page-${id}`);
  await panel.getByRole("button", { name: new RegExp(`page-${id}\\.html`) }).click();
  const frame = page.frameLocator(`iframe[title="files-${id}/page-${id}.html"]`);
  await expect(frame.getByRole("heading", { name: "Hello page" })).toBeVisible();
  // Shown, never run.
  await expect(frame.locator("body")).not.toContainText("SCRIPT RAN");

  // The tree hides from the menu, and Ctrl+P (Go to file) brings it back with the filter focused.
  await panel.getByTitle("More").click();
  await panel.getByRole("menuitem", { name: "Show file tree" }).click();
  await expect(filter).toBeHidden();
  await panel.getByRole("tab").first().click();
  await page.keyboard.press("Control+p");
  await expect(panel.getByLabel("Filter files")).toBeFocused();
});
