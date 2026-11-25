import { createHash } from "node:crypto";
import { copyFileSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

const workbook = fileURLToPath(new URL("./fixtures/supplier-quotes.xlsx", import.meta.url));

test.use({ viewport: { width: 1360, height: 880 } });

test("reads a workbook attachment and a generated workbook in the side panel", async ({ page }) => {
  const workspace = process.env.COSCRIBE_E2E_WORKSPACE;
  test.skip(!workspace, "The backend needs a workspace for the workbook.");
  const name = `supplier-${crypto.randomUUID()}.xlsx`;
  const path = join(workspace!, name);
  copyFileSync(workbook, path);
  const hash = () => createHash("sha256").update(readFileSync(path)).digest("hex");
  const before = hash();

  // The stub model does not write workbooks. Supply the output it would have recorded for this turn.
  await page.route(/\/api\/threads\/[^/]+\/activity$/, async (route) => {
    const response = await route.fetch();
    const activity = await response.json();
    activity.outputs = [{
      path: name, name, exists: true, openable: true, action: "created", modified_at: new Date(0).toISOString(),
    }];
    await route.fulfill({ response, json: activity });
  });
  await page.goto(freshThreadPath("xlsx-preview"));
  await waitForConnected(page);
  await page.locator('input[type="file"]').first().setInputFiles(path);
  await page.getByRole("button", { name: `Open ${name}`, exact: true }).click();

  const dialog = page.getByRole("dialog", { name });
  const grid = dialog.getByRole("grid", { name: "报价明细" });
  const total = grid.getByRole("gridcell", { name: "F3", exact: true });
  await total.dblclick();
  await expect(total).toHaveText("¥9,158.40");
  await expect(dialog.getByLabel("Selected cell")).toHaveText("F3");
  const formula = dialog.getByLabel("Cell formula or value");
  await expect(formula).toHaveValue("=ROUND(C3*D3*(1+E3),2)");
  await expect(formula).toHaveAttribute("readonly", "");
  await expect(grid.locator("[contenteditable]")).toHaveCount(0);
  await grid.press("ArrowDown");
  await expect(formula).toHaveValue("=ROUND(C4*D4*(1+E4),2)");
  await dialog.getByRole("button", { name: "供应商汇总" }).click();
  await expect(dialog.getByRole("figure", { name: "供应商含税报价" })).toBeVisible();
  await dialog.getByRole("button", { name: "Close", exact: true }).click();

  await page.locator("textarea").fill("The workbook is attached.");
  await page.keyboard.press("Enter");
  await page.getByTitle(`Preview ${name}`).click();
  const preview = page.getByRole("region", { name: "Excel preview" });
  await expect(preview.getByRole("grid")).toBeVisible();
  await expect(preview.getByText("Read-only")).toBeVisible();
  expect(hash()).toBe(before);
});
