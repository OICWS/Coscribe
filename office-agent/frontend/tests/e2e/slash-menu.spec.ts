import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

const many = Array.from({ length: 30 }, (_, i) => ({ name: `skill-${String(i).padStart(2, "0")}`, description: `Skill number ${i}` }));

async function serveCommands(page: Page, lists: { name: string; description: string }[][]) {
  let call = 0;
  await page.route("**/api/commands", (route) => route.fulfill({ json: lists[Math.min(call++, lists.length - 1)] }));
}

async function isInView(page: Page, name: string) {
  const item = page.getByText(`/${name}`, { exact: true });
  const menu = item.locator("xpath=../..");
  const [itemBox, menuBox] = [await item.boundingBox(), await menu.boundingBox()];
  return !!itemBox && !!menuBox && itemBox.y >= menuBox.y - 1 && itemBox.y + itemBox.height <= menuBox.y + menuBox.height + 1;
}

test("the highlighted command stays in view as the arrow keys move past the menu's edge", async ({ page }) => {
  await serveCommands(page, [many]);
  await page.goto(freshThreadPath("slash"));
  await waitForConnected(page);
  await page.locator("textarea").fill("/");
  await page.locator("textarea").press("End");
  await expect(page.getByText("/skill-00", { exact: true })).toBeVisible();

  for (let i = 0; i < 20; i++) await page.keyboard.press("ArrowDown");
  expect(await isInView(page, "skill-20")).toBe(true);

  await page.keyboard.press("ArrowUp");
  for (let i = 0; i < 19; i++) await page.keyboard.press("ArrowUp");
  expect(await isInView(page, "skill-00")).toBe(true);

  // Up from the first wraps to the last.
  await page.keyboard.press("ArrowUp");
  expect(await isInView(page, "skill-29")).toBe(true);
  await page.keyboard.press("Enter");
  await expect(page.locator("textarea")).toHaveValue("/skill-29 ");
});

test("a skill made after the page loaded is offered the next time the menu opens", async ({ page }) => {
  const made = { name: "weekly-report", description: "Write the weekly report" };
  await serveCommands(page, [many.slice(0, 2)]);
  await page.goto(freshThreadPath("slash"));
  await waitForConnected(page);
  const box = page.locator("textarea");
  await box.pressSequentially("/");
  await expect(page.getByText("/skill-01", { exact: true })).toBeVisible();
  await box.fill("");

  await page.unroute("**/api/commands");
  await serveCommands(page, [[...many.slice(0, 2), made]]);
  await box.pressSequentially("/w");
  await expect(page.getByText("/weekly-report", { exact: true })).toBeVisible();
});
