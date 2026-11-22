import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

test.use({ viewport: { width: 1440, height: 900 } });

test("a side chat answers beside the conversation, adds nothing to it and starts empty again", async ({ page }) => {
  await page.goto(freshThreadPath("side-chat"));
  await waitForConnected(page);
  await page.locator("textarea").first().fill("Reply with just the word ok.");
  await page.keyboard.press("Enter");
  await expect(page.getByText("OK", { exact: true })).toHaveCount(1);

  await page.getByTitle("Side chat", { exact: true }).click();
  const panel = page.getByRole("region", { name: "Side chat", exact: true });
  await expect(panel.getByText("Coscribe sees this session. Nothing here is added to it.")).toBeVisible();
  await panel.getByLabel("Side question").fill("What did I ask?");
  await page.keyboard.press("Enter");
  await expect(panel.getByText("OK", { exact: true })).toBeVisible();
  await expect(page.getByText("What did I ask?")).toHaveCount(1);

  await page.reload();
  await waitForConnected(page);
  await expect(page.getByText("What did I ask?")).toHaveCount(0);
  await page.getByTitle("Side chat", { exact: true }).click();
  await expect(page.getByRole("region", { name: "Side chat", exact: true }).getByText("Ask about this conversation")).toBeVisible();
});
