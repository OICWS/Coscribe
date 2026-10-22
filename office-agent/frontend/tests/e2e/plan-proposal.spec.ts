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
