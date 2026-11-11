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

test("Settings > Capabilities: files and artifacts are on, and Artifacts goes with files", async ({ page }) => {
  await page.goto(freshThreadPath("capabilities-files"));
  await waitForConnected(page);

  await page.getByTitle("Settings").click();
  await page.getByRole("button", { name: "Capabilities", exact: true }).click();

  const stored = () => page.evaluate(() => fetch("/api/capabilities").then((r) => r.json()));
  const files = page.getByRole("switch", { name: "Create and edit files" });
  const artifacts = page.getByRole("switch", { name: "Artifacts" });
  await expect(files).toHaveAttribute("aria-checked", "true");
  await expect(artifacts).toHaveAttribute("aria-checked", "true");

  await artifacts.click();
  await expect(artifacts).toHaveAttribute("aria-checked", "false");
  expect((await stored()).artifacts).toBe(false);
  await artifacts.click();
  await expect(artifacts).toHaveAttribute("aria-checked", "true");

  // With no files written, there is no artifact to make either.
  await files.click();
  await expect(files).toHaveAttribute("aria-checked", "false");
  await expect(artifacts).toHaveCount(0);
  expect((await stored()).files).toBe(false);
  await files.click();
  await expect(artifacts).toHaveAttribute("aria-checked", "true");
  expect(await stored()).toMatchObject({ files: true, artifacts: true });
});
