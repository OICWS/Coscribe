import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// The bar's buttons: the person pins some, the rest wait in the menu behind the down arrow.

async function inAConversation(page: Page) {
  await page.goto(freshThreadPath("toolbar"));
  await waitForConnected(page);
  await page.locator("textarea").fill("Reply with just the word ok.");
  await page.keyboard.press("Enter");
  await expect(page.getByTitle("Browser", { exact: true })).toBeVisible();
}

async function edit(page: Page, item: string) {
  await page.getByRole("button", { name: "More", exact: true }).click();
  await page.getByRole("menuitem", { name: "Edit toolbar" }).click();
  await page.getByRole("checkbox", { name: item }).click();
  await page.getByRole("button", { name: "Done" }).click();
}

test("Plan is always on the bar, and Artifacts waits in the menu until it is pinned", async ({ page }) => {
  await inAConversation(page);
  await expect(page.getByTitle("Plan", { exact: true })).toBeVisible();
  await expect(page.getByTitle("Artifacts", { exact: true })).toHaveCount(0);

  await page.getByRole("button", { name: "More", exact: true }).click();
  await page.getByRole("menuitem", { name: "Artifacts" }).click();
  await expect(page.getByRole("heading", { name: "Artifacts" }).first()).toBeVisible();

  await edit(page, "Artifacts");
  await expect(page.getByTitle("Artifacts", { exact: true })).toBeVisible();
});

test("an unpinned item moves into the menu, works from there and stays so after a reload", async ({ page }) => {
  await inAConversation(page);
  await edit(page, "Browser");
  await expect(page.getByTitle("Browser", { exact: true })).toHaveCount(0);

  await page.getByRole("button", { name: "More", exact: true }).click();
  await page.getByRole("menuitem", { name: "Browser" }).click();
  await expect(page.getByRole("region", { name: "Browser", exact: true })).toBeVisible();

  await page.reload();
  await waitForConnected(page);
  await expect(page.getByTitle("Browser", { exact: true })).toHaveCount(0);
});

test("the sidebar's button always stays on the bar: Edit toolbar does not list it", async ({ page }) => {
  await inAConversation(page);
  await expect(page.getByTitle("Pin navigation open")).toBeVisible();
  await page.getByRole("button", { name: "More", exact: true }).click();
  await page.getByRole("menuitem", { name: "Edit toolbar" }).click();
  await expect(page.getByRole("checkbox", { name: "Browser" })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "Sidebar" })).toHaveCount(0);
  await page.getByRole("button", { name: "Done" }).click();
  await expect(page.getByTitle("Pin navigation open")).toBeVisible();
});
