import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

async function send(page: Page, text: string): Promise<void> {
  const textarea = page.getByTestId("composer").locator("textarea");
  await textarea.fill(text);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 60_000 });
}

const bubble = (page: Page, text: string) => page.getByTestId("chat-log").getByText(text, { exact: true });

test("a sent message shows its time, and Rewind takes it and what follows out", async ({ page }) => {
  const path = freshThreadPath("rewind");
  await page.goto(path);
  await waitForConnected(page);
  await send(page, "Reply with the single word: first");
  await send(page, "Reply with the single word: second");

  await bubble(page, "Reply with the single word: second").hover();
  await expect(page.getByText("just now").last()).toBeVisible();
  await page.getByRole("button", { name: "Rewind to here" }).last().click();

  await expect(bubble(page, "Reply with the single word: second")).toHaveCount(0);
  await expect(page.getByTestId("composer").locator("textarea")).toHaveValue("Reply with the single word: second");

  // The server cut its history too: a reload replays only the first turn.
  await page.goto(path);
  await waitForConnected(page);
  await expect(bubble(page, "Reply with the single word: first")).toBeVisible();
  await expect(bubble(page, "Reply with the single word: second")).toHaveCount(0);
});

test("editing an earlier message runs from it and drops the turns after it", async ({ page }) => {
  const path = freshThreadPath("edit");
  await page.goto(path);
  await waitForConnected(page);
  await send(page, "Reply with the single word: alpha");
  await send(page, "Reply with the single word: beta");

  await bubble(page, "Reply with the single word: alpha").hover();
  await page.getByRole("button", { name: "Edit", exact: true }).first().click();
  const box = page.getByRole("textbox", { name: "Edit message" });
  await expect(page.getByRole("button", { name: "Save" })).toBeDisabled();
  await box.fill("Reply with the single word: gamma");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 60_000 });

  await page.goto(path);
  await waitForConnected(page);
  await expect(bubble(page, "Reply with the single word: gamma")).toBeVisible();
  await expect(bubble(page, "Reply with the single word: alpha")).toHaveCount(0);
  await expect(bubble(page, "Reply with the single word: beta")).toHaveCount(0);
});

test("Fork from here on an earlier reply opens a copy that ends with that reply", async ({ page }) => {
  const path = freshThreadPath("forkhere");
  await page.goto(path);
  await waitForConnected(page);
  await send(page, "Reply with the single word: one");
  await send(page, "Reply with the single word: two");
  const before = new URL(page.url()).searchParams.get("thread");

  await bubble(page, "Reply with the single word: one").hover();
  await page.getByRole("button", { name: "Fork from here" }).first().click();

  await expect.poll(() => new URL(page.url()).searchParams.get("thread")).not.toBe(before);
  await expect(bubble(page, "Reply with the single word: one")).toBeVisible();
  await expect(bubble(page, "Reply with the single word: two")).toHaveCount(0);

  // The original keeps both turns.
  await page.goto(path);
  await waitForConnected(page);
  await expect(bubble(page, "Reply with the single word: two")).toBeVisible();
});
