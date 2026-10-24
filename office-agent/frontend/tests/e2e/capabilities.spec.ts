import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

test("Settings > Capabilities: scripts on, commands off until confirmed", async ({ page }) => {
  await page.goto(freshThreadPath("capabilities"));
  await waitForConnected(page);

  await page.getByTitle("Settings").click();
  await page.getByRole("button", { name: "Capabilities", exact: true }).click();

  await expect(page.getByRole("switch", { name: "Run scripts" })).toHaveAttribute("aria-checked", "true");
  const commands = page.getByRole("switch", { name: "Run commands", exact: true });
  await expect(commands).toHaveAttribute("aria-checked", "false");

  // Turning commands on asks first; cancelling leaves them off.
  await commands.click();
  await expect(page.getByText("Turn on commands?")).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(commands).toHaveAttribute("aria-checked", "false");

  await expect(page.getByRole("button", { name: "Environment", exact: true })).toHaveCount(0);
});
