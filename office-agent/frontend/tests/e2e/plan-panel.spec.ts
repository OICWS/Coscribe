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

// A background task started while an item is in progress shows under that item with its state,
// and opens in the Background tasks panel.
test("an item lists the background task it started, and opens it", async ({ page }) => {
  test.setTimeout(240_000);
  await page.goto(freshThreadPath("plan-bg"));
  await waitForConnected(page);
  const log = page.getByTestId("chat-log");
  const send = async (text: string) => {
    await page.locator("textarea").fill(text);
    await page.keyboard.press("Enter");
    const approve = page.getByRole("button", { name: "Approve", exact: true });
    await expect(approve.or(page.getByRole("button", { name: "Send", exact: true }))).toBeVisible({ timeout: 180_000 });
    if (await approve.isVisible()) await approve.click();
    await expect(page.getByRole("button", { name: "Send", exact: true })).toBeVisible({ timeout: 180_000 });
  };

  await send('plan [[stub-tool task_create {"content":"Crunch the numbers"}]]');
  await send('go [[stub-tool task_update {"task_id":"1","status":"in_progress"}]]');
  await send('start [[stub-tool run_background_script {"language":"python","script":"print(42)","description":"Crunch"}]]');

  const started = log.getByRole("button", { name: /^Background task · / });
  await expect(started).toBeVisible({ timeout: 60_000 });
  await expect(started).toHaveText(/· (running|done)$/, { timeout: 60_000 });
  await started.click();
  await expect(page.getByText("Crunch").last()).toBeVisible();
});

// A plan put to the person outside plan mode opens the Plan panel, where its task list is edited
// before Accept; the server keeps the edited list, so it comes back after a reload.
test("the task list of a plan under review is edited before it is accepted", async ({ page }) => {
  await page.goto(freshThreadPath("plan-edit"));
  await waitForConnected(page);
  const send = async (text: string) => {
    await page.locator("textarea").fill(text);
    await page.keyboard.press("Enter");
  };
  const idle = page.getByRole("button", { name: "Send", exact: true });

  await send('a [[stub-tool task_create {"content":"Draft the memo"}]]');
  await expect(idle).toBeVisible();
  await send('b [[stub-tool task_create {"content":"Send it"}]]');
  await expect(idle).toBeVisible();
  await send('plan [[stub-tool exit_plan_mode {"plan":"# Memo plan\\n\\n1. Draft\\n2. Send"}]]');

  const card = page.getByTestId("chat-log");
  await expect(card.getByText("Claude proposed a plan")).toBeVisible();
  await expect(card.getByText("Memo plan", { exact: true })).toBeVisible();
  await page.getByRole("textbox", { name: "Step 1" }).fill("Draft a short memo");
  await page.getByRole("checkbox", { name: "Do step 2" }).uncheck();
  await page.getByRole("button", { name: "Add a step" }).click();
  await page.getByRole("textbox", { name: "Step 3" }).fill("Check it");
  await page.getByRole("button", { name: "Move step 3 up" }).click();
  await expect(card.getByText("You changed the task list")).toBeVisible();

  await card.getByRole("button", { name: "Accept", exact: true }).click();
  await expect(card.getByText("Accepted", { exact: true })).toBeVisible();

  const list = page.getByRole("heading", { name: "Tasks" }).locator("xpath=following-sibling::ol");
  await expect(list).toHaveText(/Draft a short memo.*Check it/);
  await expect(list).not.toContainText("Send it");

  await expect(idle).toBeVisible();
  await page.reload();
  await waitForConnected(page);
  await page.getByTitle("Plan", { exact: true }).click();
  const replayed = page.getByRole("heading", { name: "Tasks" }).locator("xpath=following-sibling::ol");
  await expect(replayed).toHaveText(/Draft a short memo.*Check it/);
  await expect(replayed).not.toContainText("Send it");
});
