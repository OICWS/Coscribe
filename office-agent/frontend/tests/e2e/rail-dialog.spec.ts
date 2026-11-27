import { expect, test } from "@playwright/test";
import { defaultWorkspaceName, editEnvironment, environmentNamed, freshThreadPath, newEnvironment, waitForConnected } from "./helpers";

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
  await page.getByRole("menuitem", { name: "Edit workspace" }).click();
  const dialog = page.getByRole("dialog", { name: "Edit workspace" });
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

test("a click beside the Edit workspace dialog keeps what was typed", async ({ page }) => {
  await page.goto(freshThreadPath("env-dirty"));
  await waitForConnected(page);
  await page.locator("textarea").fill("Reply with just OK.");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 30_000 });
  await page.getByTitle("Pin navigation open").click();
  await page.getByTestId("thread-row").first().click({ button: "right" });
  await page.getByRole("menuitem", { name: "Edit workspace" }).click();
  const dialog = page.getByRole("dialog", { name: "Edit workspace" });

  // Nothing typed: a click beside it closes it.
  await page.mouse.click(1270, 650);
  await expect(dialog).toHaveCount(0);

  await page.getByTestId("thread-row").first().click({ button: "right" });
  await page.getByRole("menuitem", { name: "Edit workspace" }).click();
  await dialog.getByRole("button", { name: /Environment variables/ }).click();
  await dialog.getByLabel("Environment variables", { exact: true }).fill("MODE=fast");
  await page.mouse.click(1270, 650);
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("Environment variables", { exact: true })).toHaveValue("MODE=fast");
});

test("the workspace picker makes, chooses, edits and deletes a workspace", async ({ page, request }) => {
  const path = freshThreadPath("env-picker");
  const threadId = path.split("=")[1];
  const name = `E2E env ${Math.random().toString(36).slice(2, 7)}`;
  await page.goto(path);
  await waitForConnected(page);
  const picker = page.getByTitle("Choose this conversation's workspace");
  const defaultName = await defaultWorkspaceName(request);
  await expect(picker).toHaveText(defaultName);
  await newEnvironment(page, name);

  await editEnvironment(page, name);
  const dialog = page.getByRole("dialog", { name: "Edit workspace" });
  await expect(dialog.getByText("Used by 1 conversation")).toBeVisible();
  await expect(dialog.getByRole("button", { name: /^Folder/ })).toBeVisible();
  // Every page keeps the main page's size, so the dialog does not jump while moving between them.
  const mainHeight = (await dialog.boundingBox())?.height;
  for (const page_ of ["Allowed folders", "Sites", "Secrets", "Scripts and commands", "Environment variables"]) {
    await dialog.getByRole("button", { name: new RegExp(page_) }).click();
    expect((await dialog.boundingBox())?.height).toBe(mainHeight);
    await dialog.getByRole("button", { name: "Back" }).click();
  }
  // Commands are off in Settings › Capabilities, so a workspace can't turn them on.
  await dialog.getByRole("button", { name: /Scripts and commands/ }).click();
  await expect(dialog.getByRole("switch", { name: "Commands" })).toBeDisabled();
  await dialog.getByRole("button", { name: "Back" }).click();

  await dialog.getByRole("button", { name: "Delete workspace" }).click();
  await page.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(picker).toHaveText(defaultName);
  expect(await environmentNamed(request, name)).toBeUndefined();
  await request.delete(`/api/threads/${threadId}`);
});

test("a workspace's Sites limit its conversations to the sites listed", async ({ page, request }) => {
  const path = freshThreadPath("env-network");
  const threadId = path.split("=")[1];
  const name = `E2E net ${Math.random().toString(36).slice(2, 7)}`;
  await page.goto(path);
  await waitForConnected(page);
  await newEnvironment(page, name);
  try {
    await editEnvironment(page, name);
    const dialog = page.getByRole("dialog", { name: "Edit workspace" });
    await dialog.getByRole("button", { name: /^Sites/ }).click();
    await expect(dialog.getByRole("button", { name: "Any site", pressed: true })).toBeVisible();
    await dialog.getByRole("button", { name: "Listed sites" }).click();

    const site = dialog.getByLabel("Add a site");
    await site.fill("not a domain");
    await site.press("Enter");
    await expect(dialog.getByText("isn't a site")).toBeVisible();
    await site.fill("https://www.example.com/page");
    await site.press("Enter");
    await site.fill("docs.python.org");
    await dialog.getByRole("button", { name: "Add site" }).click();
    await expect(dialog.getByRole("cell", { name: "example.com", exact: true })).toBeVisible();
    await dialog.getByRole("button", { name: "example.com in the browser" }).click();
    await page.getByRole("menuitemradio", { name: "Use without asking" }).click();
    await dialog.getByRole("button", { name: "Save changes" }).click();
    await expect(dialog).toHaveCount(0);
    expect((await environmentNamed(request, name))?.network).toEqual({
      mode: "limited",
      domains: ["example.com", "docs.python.org"],
      browser: { "example.com": "allow" },
    });

    // The Browser panel's prompt keeps a level the same way, in the conversation's workspace.
    const kept = await request.post(`/api/threads/${threadId}/browser-site`, { data: { site: "docs.python.org", level: "off" } });
    expect(kept.ok()).toBe(true);
    await editEnvironment(page, name);
    await dialog.getByRole("button", { name: /^Sites/ }).click();
    await expect(dialog.getByRole("button", { name: "Listed sites", pressed: true })).toBeVisible();
    await expect(dialog.getByRole("button", { name: "docs.python.org in the browser" })).toHaveText("Not in the browser");
    await dialog.getByRole("button", { name: "Remove docs.python.org" }).click();
    await dialog.getByRole("button", { name: "None", exact: true }).click();
    await expect(dialog.getByLabel("Add a site")).toHaveCount(0);
    await dialog.getByRole("button", { name: "Save changes" }).click();
    await expect(dialog).toHaveCount(0);
    expect((await environmentNamed(request, name))?.network).toEqual({ mode: "none", domains: [] });
  } finally {
    const env = await environmentNamed(request, name);
    if (env) await request.delete(`/api/environments/${env.id}`);
    await request.delete(`/api/threads/${threadId}`);
  }
});
