import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// Only the list: choosing one rebuilds the shared server's script environment, which the
// pytest suite covers (tests/web/test_settings.py, tests/test_find_python.py).
test("Settings > Capabilities lists the Pythons found, Automatic first", async ({ page }) => {
  await page.goto(freshThreadPath("python-interpreter"));
  await waitForConnected(page);

  await page.getByTitle("Settings").click();
  await page.getByRole("button", { name: "Capabilities", exact: true }).click();

  await page.getByRole("button", { name: /Show Python and packages/ }).click();

  await expect(page.getByRole("radio", { name: /^Automatic/ })).toBeChecked();
  await expect(page.getByRole("radio", { name: /^Python 3\.\d+/ }).first()).toBeVisible();
  // coscribe's own Python is a Windows build: nothing to offer on the Linux runner.
  await expect(page.getByRole("button", { name: /Download \(about 30 MB\)/ })).toHaveCount(0);
});
