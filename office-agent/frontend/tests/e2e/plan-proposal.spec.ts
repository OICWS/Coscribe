import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// A plan proposed in plan mode: the source row, the card with its choices, and the answer it records.
test("a proposed plan can be opened, revised and rejected", async ({ page }) => {
  await page.goto(freshThreadPath("plan-proposal"));
  await waitForConnected(page);
  const send = async (text: string) => {
    await page.locator("textarea").fill(text);
    await page.keyboard.press("Enter");
  };

  await send("/plan");
  await send('plan it [[stub-tool exit_plan_mode {"plan":"# Memo plan\\n\\n1. Read the notes"}]]');
  await expect(page.getByText("Claude proposed a plan")).toBeVisible();
  for (const name of ["Reject", "Revise…", "Accept", "Accept and auto mode", "Open plan"]) {
    await expect(page.getByRole("button", { name, exact: true })).toBeVisible();
  }

  await page.getByRole("button", { name: "Proposing plan" }).click();
  await expect(page.locator("pre", { hasText: "1. Read the notes" })).toBeVisible();

  await page.getByRole("button", { name: "Open plan", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Memo plan" })).toBeVisible();

  await page.getByRole("button", { name: "Revise…" }).click();
  await expect(page.getByPlaceholder("What should change? (optional)")).toBeVisible();
  await page.getByTestId("chat-log").getByRole("button", { name: "Back", exact: true }).click();

  await page.getByRole("button", { name: "Reject", exact: true }).click();
  await expect(page.getByText("Rejected. Nothing will be done")).toBeVisible();
});

// A plan proposed again after a revision is shown as what changed.
test("a revised plan shows the diff against the one before", async ({ page }) => {
  await page.goto(freshThreadPath("plan-diff"));
  await waitForConnected(page);
  const send = async (text: string) => {
    await page.locator("textarea").fill(text);
    await page.keyboard.press("Enter");
  };

  await send("/plan");
  await send('plan it [[stub-tool exit_plan_mode {"plan":"# Memo plan\\n\\n1. Read the notes\\n2. Write it"}]]');
  await expect(page.getByRole("button", { name: /Created plan/ })).toContainText("+4");

  await page.getByRole("button", { name: "Revise…" }).click();
  await page.getByPlaceholder("What should change? (optional)").fill("Add a review step");
  await page.getByTestId("chat-log").getByRole("button", { name: "Revise", exact: true }).click();
  await expect(page.getByText("Sent back with your feedback")).toBeVisible();

  await send('again [[stub-tool exit_plan_mode {"plan":"# Memo plan\\n\\n1. Read the notes\\n2. Write it\\n3. Review it"}]]');
  const updated = page.getByRole("button", { name: /Updated plan/ });
  await expect(updated).toContainText("+1");
  await updated.click();
  await expect(page.getByText("3. Review it").last()).toBeVisible();
});
