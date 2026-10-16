import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

test.use({ viewport: { width: 1440, height: 900 } });

const box = async (page: Page, name: string) => {
  const found = await page.getByRole("region", { name, exact: true }).boundingBox();
  if (!found) throw new Error(`no ${name} panel`);
  return found;
};

test("panels open together, move by dragging and from the menu, and fill the window", async ({ page }) => {
  await page.goto(freshThreadPath("panels"));
  await page.evaluate(() => localStorage.removeItem("coscribe.panelLayout"));
  await page.reload();
  await waitForConnected(page);
  await page.locator("textarea").fill("Reply with just the word ok.");
  await page.keyboard.press("Enter");

  await page.getByTitle("Show task details").click();
  await page.getByTitle("Background tasks", { exact: true }).click();
  const task = await box(page, "Task details");
  const background = await box(page, "Background tasks");
  expect(background.x).toBeGreaterThan(task.x + task.width - 1);

  // Dragged by its header onto the lower part of Task details: below it.
  await page.mouse.move(background.x + 60, background.y + 22);
  await page.mouse.down();
  await page.mouse.move(background.x + 90, background.y + 60, { steps: 4 });
  await page.mouse.move(task.x + task.width / 2, task.y + task.height - 30, { steps: 10 });
  await page.mouse.up();
  await expect(async () => {
    const [t, b] = [await box(page, "Task details"), await box(page, "Background tasks")];
    expect(Math.abs(b.x - t.x)).toBeLessThan(2);
    expect(b.y).toBeGreaterThan(t.y + t.height - 1);
  }).toPass();

  // From the expand button's menu: along the left of everything.
  await page.getByRole("button", { name: "Expand Background tasks" }).hover();
  await page.getByRole("menuitem", { name: "Move to the left" }).click();
  await expect(async () => {
    const [t, b] = [await box(page, "Task details"), await box(page, "Background tasks")];
    expect(b.x + b.width).toBeLessThan(t.x);
  }).toPass();

  // Clicked, the expand button fills the window; Escape gives the conversation back.
  await page.getByRole("button", { name: "Expand Task details" }).click();
  await expect(page.getByRole("region", { name: "Background tasks", exact: true })).toBeHidden();
  expect((await box(page, "Task details")).width).toBeGreaterThan(1300);
  await page.mouse.move(700, 450);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("region", { name: "Background tasks", exact: true })).toBeVisible();

  // The arrangement is kept on this computer.
  await page.reload();
  await waitForConnected(page);
  await page.getByTitle("Show task details").click();
  await page.getByTitle("Background tasks", { exact: true }).click();
  await expect(async () => {
    const [t, b] = [await box(page, "Task details"), await box(page, "Background tasks")];
    expect(b.x + b.width).toBeLessThan(t.x);
  }).toPass();
});
