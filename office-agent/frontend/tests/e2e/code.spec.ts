import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

test("Settings has the code module under Capabilities", async ({ page }) => {
  await page.goto(freshThreadPath("code-settings"));
  await waitForConnected(page);

  await page.getByTitle("Settings").click();
  await page.getByRole("button", { name: "Capabilities", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Code module" })).toBeVisible();
  await expect(page.getByLabel("Model for code")).toBeVisible();
  await expect(page.getByRole("switch", { name: "Chats can hand tasks to Code" })).toBeVisible();
});

test("The nav rail has no Code mode", async ({ page }) => {
  await page.goto(freshThreadPath("code-nav"));
  await waitForConnected(page);

  await page.getByTitle("Pin navigation open").click();
  await expect(page.getByTitle("Scheduled", { exact: true })).toBeVisible();
  await expect(page.getByTitle("Code", { exact: true })).toHaveCount(0);
});

test("Settings > Capabilities can allow file changes for good, and offers no switch for commands", async ({ page }) => {
  await page.goto(freshThreadPath("code-approvals"));
  await waitForConnected(page);

  await page.getByTitle("Settings").click();
  await page.getByRole("button", { name: "Capabilities", exact: true }).click();

  await expect(page.getByRole("switch", { name: "Run commands without asking" })).toHaveCount(0);
  await expect(page.getByText("Codex can't run commands")).toBeVisible();
  const changes = page.getByRole("switch", { name: "Change files without asking" });
  await expect(changes).toHaveAttribute("aria-checked", "false");
  await changes.click();
  await expect(changes).toHaveAttribute("aria-checked", "true");
  await changes.click();
  await expect(changes).toHaveAttribute("aria-checked", "false");
});
