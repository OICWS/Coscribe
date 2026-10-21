import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// The task list the model keeps shows as one card in the conversation and in the Plan panel.
test("a task list is a card in the conversation and a list in the Plan panel", async ({ page }) => {
  await page.goto(freshThreadPath("plan-panel"));
  await waitForConnected(page);
  const send = async (text: string) => {
    await page.locator("textarea").fill(text);
    await page.keyboard.press("Enter");
  };

  await send('start [[stub-tool task_create {"content":"Draft the memo"}]]');
  const card = page.getByText("Draft the memo", { exact: true });
  await expect(card).toBeVisible();
  await expect(page.getByRole("img", { name: "To do" })).toBeVisible();

  await send('finish [[stub-tool task_update {"task_id":"1","status":"completed"}]]');
  await expect(page.getByRole("img", { name: "Done" })).toBeVisible();

  await page.getByTitle("Plan", { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  const list = page.getByRole("heading", { name: "Tasks" }).locator("xpath=following-sibling::ol");
  await expect(list).toContainText("Draft the memo");
  await expect(list.getByRole("img", { name: "Done" })).toBeVisible();
});
