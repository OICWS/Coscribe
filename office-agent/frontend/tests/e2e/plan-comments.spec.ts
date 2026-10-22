import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// Words selected in the Plan panel become comments that travel with Revise.
test("a comment on selected plan text is sent with the revision", async ({ page }) => {
  await page.goto(freshThreadPath("plan-comments"));
  await waitForConnected(page);
  const send = async (text: string) => {
    await page.locator("textarea").fill(text);
    await page.keyboard.press("Enter");
  };

  await send("/plan");
  await send('plan it [[stub-tool exit_plan_mode {"plan":"# Memo plan\\n\\n1. Read the notes\\n2. Write it"}]]');
  await page.getByRole("button", { name: "Open plan", exact: true }).click();

  await expect(page.locator(".plan-doc li", { hasText: "Write it" })).toBeVisible();
  await page.evaluate(() => {
    const item = [...document.querySelectorAll(".plan-doc li")].find((li) => li.textContent?.includes("Write it"));
    const range = document.createRange();
    range.selectNodeContents(item!);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);
    item!.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
  });
  const box = page.getByPlaceholder("Add a comment");
  await expect(box).toBeVisible();
  await box.fill("Name the file");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Comments" })).toBeVisible();
  await expect(page.getByText("Name the file")).toBeVisible();

  await page.getByRole("button", { name: "Revise…" }).click();
  await page.getByTestId("chat-log").getByRole("button", { name: "Revise", exact: true }).click();
  await expect(page.getByText("Sent back with your feedback")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Comments" })).toBeHidden();
});
