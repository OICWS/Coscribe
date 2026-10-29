import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// While a deck is being built from pages, the panel shows the pages written so far (the stub model
// writes one file per message, then a slow command keeps the turn running).
test.use({ viewport: { width: 1600, height: 1000 } });

const svg = (color: string) => `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1280 720'><rect width='1280' height='720' fill='${color}'/></svg>`;

test("the Slides panel shows the pages written so far until the deck is built", async ({ page }) => {
  test.setTimeout(150_000);
  await page.goto(freshThreadPath("slides-drafts"));
  await waitForConnected(page);
  const write = async (path: string, content: string) => {
    await page.locator("textarea").fill(`write ${path} [[stub-tool write_file ${JSON.stringify({ path, content })}]]`);
    await page.keyboard.press("Enter");
    await page.getByRole("button", { name: "Approve", exact: true }).click({ timeout: 30_000 });
    await expect(page.getByText(`write ${path}`, { exact: false }).first()).toBeVisible();
    await page.waitForTimeout(1200);
  };
  await write("pages/01-cover.svg", svg("#0a6"));
  await write("pages/02-agenda.svg", svg("#06a"));
  await write("pages/03-body.svg", svg("#a60"));
  await write("deck.pptx", "not built from pages");

  const script = "import time\ntime.sleep(45)";
  await page.locator("textarea").fill(`wait [[stub-tool run_python_script ${JSON.stringify({ script, description: "wait" })}]]`);
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Approve", exact: true }).click({ timeout: 30_000 });
  await expect(page.getByRole("button", { name: "Run in background" })).toBeVisible({ timeout: 30_000 });

  await page.getByTitle(/task/i).first().click();
  await page.locator("li", { hasText: "Created today" }).filter({ hasText: "deck.pptx" }).getByRole("button").first().click({ timeout: 15_000 });
  await expect(page.getByText("3 pages so far")).toBeVisible();
  await expect(page.getByRole("img", { name: "01-cover.svg" })).toBeVisible();
  await expect(page.getByRole("img", { name: "03-body.svg" })).toBeVisible();
});
