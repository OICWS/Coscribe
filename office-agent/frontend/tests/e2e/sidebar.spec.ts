import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

async function startThread(page: Page, prefix: string): Promise<string> {
  const path = freshThreadPath(prefix);
  await page.goto(path);
  await waitForConnected(page);
  await page.locator("textarea").fill("Reply with just OK.");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 30_000 });
  return new URL(path, "http://x").searchParams.get("thread") ?? "";
}

test("sessions can be grouped, filtered, archived and brought back", async ({ page, request }) => {
  const first = await startThread(page, "side-a");
  const second = await startThread(page, "side-b");
  try {
    await page.getByTitle("Pin navigation open").click();
    const rows = page.getByTestId("thread-row");
    await expect(rows.first()).toBeVisible();

    // Right-click: move into a new group.
    await rows.first().click({ button: "right" });
    await page.getByRole("menuitem", { name: "Move to group" }).click();
    await page.getByRole("menuitem", { name: "New group…" }).click();
    await page.getByLabel("New group name").fill("E2E group");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("button", { name: /^E2E group/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /^Ungrouped/ })).toBeVisible();

    // The group can be collapsed.
    const header = page.getByRole("button", { name: /^E2E group/ });
    await header.click();
    await expect(header).toHaveAttribute("aria-expanded", "false");
    await header.click();

    // Drag a session between groups and back.
    const inGroup = page.locator('[data-testid="thread-section"][data-group="E2E group"]').getByTestId("thread-row");
    const ungrouped = page.locator('[data-testid="thread-section"][data-group=""]');
    await expect(inGroup).toHaveCount(1);
    await ungrouped.getByTestId("thread-row").first().dragTo(header);
    await expect(inGroup).toHaveCount(2);
    await inGroup.first().dragTo(page.getByRole("button", { name: /^Ungrouped/ }));
    await expect(inGroup).toHaveCount(1);

    // Archive the first row: it leaves the list and shows under Archived.
    const before = await rows.count();
    await rows.first().click({ button: "right" });
    await page.getByRole("menuitem", { name: "Archive" }).click();
    await expect(rows).toHaveCount(before - 1);
    await page.getByTitle("Filter sessions").click();
    await page.getByRole("menuitemradio", { name: "Archived" }).click();
    await expect(rows.first()).toBeVisible();
    const archived = await rows.count();

    // Unarchive from there.
    await rows.first().click({ button: "right" });
    await page.getByRole("menuitem", { name: "Unarchive" }).click();
    await expect(rows).toHaveCount(archived - 1);
    await page.getByTitle("Filter sessions").click();
    await page.getByRole("menuitemradio", { name: "All" }).click();
    await expect(rows).toHaveCount(before);
  } finally {
    for (const id of [first, second]) await request.delete(`/api/threads/${id}`);
    await request.delete("/api/thread-groups/E2E%20group");
  }
});

test("a deleted session shows it is being deleted, then leaves; a failed delete says so", async ({ page, request }) => {
  const first = await startThread(page, "del-a");
  const second = await startThread(page, "del-b");
  try {
    await page.getByTitle("Pin navigation open").click();
    const rows = page.getByTestId("thread-row");
    await expect(rows.first()).toBeVisible();
    const before = await rows.count();

    // Held until the row has shown that it is being deleted.
    let release = () => {};
    const held = new Promise<void>((resolve) => (release = resolve));
    await page.route(`**/api/threads/${first}`, async (route) => {
      if (route.request().method() === "DELETE") await held;
      await route.continue();
    });
    await page.route(`**/api/threads/${second}`, (route) =>
      route.request().method() === "DELETE" ? route.fulfill({ status: 500, json: { error: "x" } }) : route.continue(),
    );
    const deleteRow = async (index: number) => {
      await rows.nth(index).click({ button: "right" });
      await page.getByRole("menuitem", { name: "Delete" }).click();
      await page.getByRole("button", { name: "Delete", exact: true }).click();
    };

    // The newest row is `second`, the one after it `first`.
    await deleteRow(1);
    await expect(page.locator('[data-deleting="true"]')).toHaveText(/Deleting…/);
    release();
    await expect(rows).toHaveCount(before - 1);

    await deleteRow(0);
    await expect(rows.first()).toContainText("Not deleted");
    await expect(rows).toHaveCount(before - 1);
  } finally {
    for (const id of [first, second]) await request.delete(`/api/threads/${id}`);
  }
});
