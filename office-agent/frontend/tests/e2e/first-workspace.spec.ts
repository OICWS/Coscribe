import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// The shared backend's workspace is chosen once, in the workflow's setup; the first start is
// played here with the two calls answered by the test.
test("the first start asks for a workspace, offers one, and saves the folder chosen", async ({ page }) => {
  let chosen: unknown = null;
  await page.route("**/api/workspace/first", (route) => {
    if (route.request().method() === "GET") return route.fulfill({ json: { needed: chosen === null, suggested: "/home/someone/Documents/Coscribe" } });
    chosen = route.request().postDataJSON();
    return route.fulfill({ json: { folder: "/home/someone/Documents/Coscribe" } });
  });
  await page.goto(freshThreadPath("first-workspace"));
  await waitForConnected(page);

  const dialog = page.getByRole("dialog", { name: "Choose a workspace" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("/home/someone/Documents/Coscribe")).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Change…" })).toBeVisible();
  await dialog.getByRole("button", { name: "Use this folder" }).click();

  await expect.poll(() => chosen).toEqual({ folder: "/home/someone/Documents/Coscribe" });
  await expect(dialog).toHaveCount(0);
});

test("a refused folder says why and the dialog stays", async ({ page }) => {
  await page.route("**/api/workspace/first", (route) =>
    route.request().method() === "GET"
      ? route.fulfill({ json: { needed: true, suggested: "/nowhere/Coscribe" } })
      : route.fulfill({ status: 422, json: { error: "/nowhere doesn't exist." } }),
  );
  await page.goto(freshThreadPath("first-workspace-refused"));
  const dialog = page.getByRole("dialog", { name: "Choose a workspace" });
  await dialog.getByRole("button", { name: "Use this folder" }).click();
  await expect(dialog.getByRole("alert")).toHaveText("/nowhere doesn't exist.");
  await expect(dialog).toBeVisible();
});
