import { closeSync, ftruncateSync, openSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

const workspace = process.env.COSCRIBE_E2E_WORKSPACE;
test.skip(!workspace, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");

test("Files renders a Doc chart and waits for an explicit request before opening a large workbook", async ({ page }) => {
  const suffix = crypto.randomUUID();
  const doc = `report-${suffix}.md`;
  const large = `budget-${suffix}.xlsx`;
  writeFileSync(join(workspace!, doc), [
    "---", "coscribe: doc", "---", "", "# Quote summary", "", "```chart", "bar Prices",
    "| Vendor | Total |", "| --- | --- |", "| Elm | 100 |", "| Oak | 220 |", "```", "",
  ].join("\n"));
  const descriptor = openSync(join(workspace!, large), "w");
  try {
    ftruncateSync(descriptor, 3 * 1024 * 1024);
  } finally {
    closeSync(descriptor);
  }

  await page.goto(freshThreadPath("unified-preview"));
  await waitForConnected(page);
  await page.locator("textarea").fill("Reply with OK.");
  await page.keyboard.press("Enter");
  await page.getByTitle("Files", { exact: true }).click();
  const files = page.getByRole("region", { name: "Files" });
  const filter = files.getByLabel("Filter files");

  await filter.fill(doc);
  await files.getByRole("button", { name: doc, exact: true }).click();
  await expect(files.getByRole("heading", { name: "Quote summary" })).toBeVisible();
  await expect(files.locator(".doc-chart svg")).toBeVisible();
  await expect(files.locator("[contenteditable=true]")).toHaveCount(0);
  await files.getByTitle("View source").click();
  await expect(files.getByText("coscribe: doc", { exact: true })).toBeVisible();

  let requests = 0;
  page.on("request", (request) => {
    if (request.url().includes("/api/attachment/xlsx")) requests += 1;
  });
  await filter.fill(large);
  await files.getByRole("button", { name: large, exact: true }).click();
  await expect(files.getByText("This file may take a while to preview.")).toBeVisible();
  await expect(files.getByRole("button", { name: "Open in its app" })).toBeVisible();
  expect(requests).toBe(0);
  const explicit = page.waitForResponse((response) => response.url().includes("/api/attachment/xlsx"));
  await files.getByRole("button", { name: "Open in Viewer" }).click();
  await explicit;
  expect(requests).toBeGreaterThan(0);
});
