import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

const workspace = process.env.COSCRIBE_E2E_WORKSPACE ?? "";
test.skip(!workspace, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({ viewport: { width: 1280, height: 860 } });

// A 1x1 PNG, enough for a thumbnail to load from the server.
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg==", "base64");

test("what the conversation made shows as notices above the message box, each kind its own way", async ({ page }) => {
  const id = Math.random().toString(36).slice(2, 8);
  const folder = `made-${id}`;
  mkdirSync(join(workspace, folder), { recursive: true });
  for (const name of ["chart-1.png", "chart-2.png"]) writeFileSync(join(workspace, folder, name), PNG);
  const now = new Date().toISOString();
  const file = (name: string, openable: boolean) => ({
    path: `${folder}/${name}`,
    name,
    exists: true,
    openable,
    modified_at: now,
    action: "created",
  });
  // The stub model writes nothing, so the conversation's outputs are given as a real turn would leave them.
  await page.route(/\/api\/threads\/[^/]+\/activity$/, async (route) => {
    const response = await route.fetch();
    const activity = await response.json();
    activity.outputs = [file(`budget-${id}.xlsx`, true), file("chart-2.png", true), file("chart-1.png", true), file(`review-${id}.pptx`, true)];
    await route.fulfill({ response, json: activity });
  });

  await page.goto(freshThreadPath("notices"));
  await waitForConnected(page);
  await page.locator("textarea").fill("Reply with just the word ok.");
  await page.keyboard.press("Enter");

  const notices = page.getByTestId("notice");
  await expect(notices.first()).toBeVisible();
  await expect(page.getByRole("button", { name: /Show 1 more/ })).toBeVisible();
  await page.getByRole("button", { name: /Show 1 more/ }).click();
  await expect(notices).toHaveCount(3);

  const deck = notices.filter({ hasText: `review-${id}` });
  await expect(deck).toContainText("Presentation");
  const pictures = notices.filter({ hasText: "2 pictures" });
  await expect(pictures.locator("img")).toHaveCount(2);
  const sheet = notices.filter({ hasText: `budget-${id}.xlsx` });
  await expect(sheet).toContainText("Excel");
  await expect(sheet.getByRole("button", { name: "Open" })).toBeVisible();
  await expect(sheet.getByRole("button", { name: /Show in folder/ })).toBeVisible();
  await page.screenshot({ path: "test-results/output-notices.png" });

  await pictures.getByRole("button", { name: "View all" }).click();
  const viewer = page.getByRole("dialog");
  await expect(viewer).toBeVisible();
  await expect(viewer.getByRole("button", { name: "Copy" })).toBeVisible();
  await page.screenshot({ path: "test-results/output-notices-viewer.png" });
  await page.keyboard.press("Escape");
  await expect(viewer).toBeHidden();

  // A closed notice stays closed until its file changes again.
  await deck.getByRole("button", { name: "Close" }).click();
  await expect(notices.filter({ hasText: `review-${id}` })).toHaveCount(0);
  await page.reload();
  await waitForConnected(page);
  await expect(notices.filter({ hasText: `budget-${id}.xlsx` })).toBeVisible();
  await expect(notices.filter({ hasText: `review-${id}` })).toHaveCount(0);
});
