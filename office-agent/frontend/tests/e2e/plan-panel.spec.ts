import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// The task list the model keeps shows as one card under the latest change to it, folds into one
// line once every item is done, and is a list in the Plan panel.
test("a task list follows its changes down the conversation and folds when done", async ({ page }) => {
  await page.goto(freshThreadPath("plan-panel"));
  await waitForConnected(page);
  const send = async (text: string) => {
    await page.locator("textarea").fill(text);
    await page.keyboard.press("Enter");
    await expect(page.getByRole("button", { name: "Send", exact: true })).toBeVisible();
  };
  const log = page.getByTestId("chat-log");

  await send('start [[stub-tool task_create {"content":"Draft the memo"}]]');
  await expect(log.getByText("Draft the memo", { exact: true })).toBeVisible();
  await expect(log.getByRole("img", { name: "To do" })).toBeVisible();

  // A second change, a turn later: the card moves down, and the first place keeps no copy.
  await send('more [[stub-tool task_create {"content":"Send it"}]]');
  await expect(log.getByText("Draft the memo", { exact: true })).toHaveCount(1);
  await expect(log.getByText("Steps · 0 of 2 done")).toBeVisible();
  const top = async (text: string | RegExp) => (await log.getByText(text, { exact: true }).first().boundingBox())?.y ?? 0;
  expect(await top("Draft the memo")).toBeGreaterThan(await top(/^more /));

  await send('finish [[stub-tool task_update {"task_id":"1","status":"completed"}]]');
  await send('last [[stub-tool task_update {"task_id":"2","status":"completed"}]]');
  const done = log.getByRole("button", { name: /2 steps done/ });
  await expect(done).toBeVisible();
  await expect(log.getByText("Draft the memo", { exact: true })).toHaveCount(0);
  await done.click();
  await expect(log.getByRole("img", { name: "Done" })).toHaveCount(2);

  await page.getByTitle("Plan", { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  const list = page.getByRole("heading", { name: "Tasks" }).locator("xpath=following-sibling::ol");
  await expect(list).toContainText("Draft the memo");
  await expect(list.getByRole("img", { name: "Done" })).toHaveCount(2);
});
