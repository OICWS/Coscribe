import { expect, test } from "@playwright/test";
import { editEnvironment, environmentNamed, freshThreadPath, newEnvironment, waitForConnected } from "./helpers";

test("a dialog opened from a hover-opened sidebar is not closed with the sidebar", async ({ page }) => {
  await page.goto(freshThreadPath("rail-dialog"));
  await waitForConnected(page);
  await page.locator("textarea").fill("Reply with just OK.");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 30_000 });

  // Not pinned: the pointer over the top-left corner opens it.
  await page.mouse.move(20, 20);
  const row = page.getByTestId("thread-row").first();
  await expect(row).toBeVisible();
  await row.click({ button: "right" });
  await page.getByRole("menuitem", { name: "Edit environment" }).click();
  const dialog = page.getByRole("dialog", { name: "Edit environment" });
  await expect(dialog).toBeVisible();

  // Into the dialog, well clear of the sidebar, and longer than its delay.
  await page.mouse.move(700, 400);
  await page.waitForTimeout(1500);
  await expect(dialog).toBeVisible();

  // The window losing focus (the Windows screenshot tool, an alt-tab) collapses a
  // hover-opened sidebar too.
  await page.evaluate(() => window.dispatchEvent(new Event("blur")));
  await page.waitForTimeout(500);
  await expect(dialog).toBeVisible();

  // Closed, and the pointer still out of the sidebar: it goes with the next move.
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await page.mouse.move(720, 420);
  await expect(page.getByTestId("thread-row")).toHaveCount(0, { timeout: 3000 });
});

test("a click beside the Edit environment dialog keeps what was typed", async ({ page }) => {
  await page.goto(freshThreadPath("env-dirty"));
  await waitForConnected(page);
  await page.locator("textarea").fill("Reply with just OK.");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 30_000 });
  await page.getByTitle("Pin navigation open").click();
  await page.getByTestId("thread-row").first().click({ button: "right" });
  await page.getByRole("menuitem", { name: "Edit environment" }).click();
  const dialog = page.getByRole("dialog", { name: "Edit environment" });

  // Nothing typed: a click beside it closes it.
  await page.mouse.click(1270, 650);
  await expect(dialog).toHaveCount(0);

  await page.getByTestId("thread-row").first().click({ button: "right" });
  await page.getByRole("menuitem", { name: "Edit environment" }).click();
  await dialog.getByRole("button", { name: /Environment variables/ }).click();
  await dialog.getByLabel("Environment variables", { exact: true }).fill("MODE=fast");
  await page.mouse.click(1270, 650);
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("Environment variables", { exact: true })).toHaveValue("MODE=fast");
});

test("the environment picker makes, chooses, edits and deletes an environment", async ({ page, request }) => {
  const path = freshThreadPath("env-picker");
  const threadId = path.split("=")[1];
  const name = `E2E env ${Math.random().toString(36).slice(2, 7)}`;
  await page.goto(path);
  await waitForConnected(page);
  const picker = page.getByTitle("Choose this conversation's environment");
  await expect(picker).toHaveText("Default");
  await newEnvironment(page, name);

  await editEnvironment(page, name);
  const dialog = page.getByRole("dialog", { name: "Edit environment" });
  await expect(dialog.getByText("Used by 1 conversation")).toBeVisible();
  for (const page_ of ["Folders", "Network", "Scripts and commands", "Secrets", "Environment variables"]) {
    await expect(dialog.getByRole("button", { name: new RegExp(page_) })).toBeVisible();
  }
  // Every page keeps the main page's size, so the dialog does not jump while moving between them.
  const mainHeight = (await dialog.boundingBox())?.height;
  for (const page_ of ["Folders", "Network", "Scripts and commands", "Secrets", "Environment variables"]) {
    await dialog.getByRole("button", { name: new RegExp(page_) }).click();
    expect((await dialog.boundingBox())?.height).toBe(mainHeight);
    await dialog.getByRole("button", { name: "Back" }).click();
  }
  // Commands are off in Settings › Capabilities, so an environment can't turn them on.
  await dialog.getByRole("button", { name: /Scripts and commands/ }).click();
  await expect(dialog.getByRole("switch", { name: "Commands" })).toBeDisabled();
  await dialog.getByRole("button", { name: "Back" }).click();

  await dialog.getByRole("button", { name: "Delete environment" }).click();
  await page.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(picker).toHaveText("Default");
  expect(await environmentNamed(request, name)).toBeUndefined();
  await request.delete(`/api/threads/${threadId}`);
});

test("an environment's Network page limits its conversations to the domains given", async ({ page, request }) => {
  const path = freshThreadPath("env-network");
  const threadId = path.split("=")[1];
  const name = `E2E net ${Math.random().toString(36).slice(2, 7)}`;
  await page.goto(path);
  await waitForConnected(page);
  await newEnvironment(page, name);
  try {
    await editEnvironment(page, name);
    const dialog = page.getByRole("dialog", { name: "Edit environment" });
    await expect(dialog.getByRole("button", { name: /Network/ })).toContainText("Limited: any site, scripts offline");
    await dialog.getByRole("button", { name: /Network/ }).click();
    await expect(dialog.getByRole("radio", { name: /Limited/ })).toBeChecked();

    await dialog.getByLabel("Allowed domains").fill("not a domain");
    await dialog.getByRole("button", { name: "Save changes" }).click();
    await expect(dialog.getByText("isn't a domain")).toBeVisible();

    await dialog.getByLabel("Allowed domains").fill("https://www.example.com/page\ndocs.python.org");
    await dialog.getByRole("button", { name: "Save changes" }).click();
    await expect(dialog).toHaveCount(0);
    expect((await environmentNamed(request, name))?.network).toEqual({
      mode: "limited",
      domains: ["example.com", "docs.python.org"],
    });

    await editEnvironment(page, name);
    await expect(dialog.getByRole("button", { name: /Network/ })).toContainText("Limited: 2 domains");
    await dialog.getByRole("button", { name: /Network/ }).click();
    await dialog.getByRole("radio", { name: /None/ }).check();
    await expect(dialog.getByLabel("Allowed domains")).toHaveCount(0);
    await dialog.getByRole("button", { name: "Save changes" }).click();
    await expect(dialog).toHaveCount(0);
    expect((await environmentNamed(request, name))?.network).toEqual({ mode: "none", domains: [] });
  } finally {
    const env = await environmentNamed(request, name);
    if (env) await request.delete(`/api/environments/${env.id}`);
    await request.delete(`/api/threads/${threadId}`);
  }
});
