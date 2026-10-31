import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

const workspace = process.env.COSCRIBE_E2E_WORKSPACE ?? "";
test.skip(!workspace, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({ viewport: { width: 1600, height: 1000 } });

const PAGE =
  '<html><head><meta name=\\"coscribe\\" content=\\"dashboard\\"></head><body>' +
  '<h1>Sales</h1><div style=\\"padding:20px;font-size:28px\\" data-figure=\\"total\\">-</div>' +
  "<script>document.querySelector('[data-figure]').textContent = window.coscribe.figures.total.value;</script></body></html>";

test("a dashboard says when its data was made, refreshes, and shows where a figure came from", async ({ page }) => {
  const name = `dash-${Math.random().toString(36).slice(2, 8)}`;
  const folder = join(workspace, `${name}.dashboard`);
  mkdirSync(join(folder, "data"), { recursive: true });
  const datasets = {
    datasets: { q3: { title: "Q3 sales", source: "q3.csv", updated: "2026-10-28T08:10:00" } },
    figures: { total: { label: "Total sales", value: 1520, formula: "sum of q3 sales", from: ["q3"] } },
  };
  writeFileSync(join(folder, "datasets.json"), JSON.stringify(datasets));
  writeFileSync(join(folder, "data", "q3.json"), JSON.stringify([{ region: "East", sales: 1520 }]));

  await page.goto(freshThreadPath(name));
  await waitForConnected(page);
  await page.locator("textarea").fill(`make it [[stub-tool write_file {"path":"${name}.html","content":"${PAGE}"}]] [[stub-say I wrote ${name}.html.]]`);
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByTitle(`Open ${name}.html`).click();

  await expect(page.getByText(/^Data from /)).toBeVisible();
  const frame = page.frameLocator(`iframe[title="${name}.html"]`);
  const figure = frame.locator("[data-figure=total]");
  await expect(figure).toHaveText("1520");
  // hover() scrolls the figure into view first, and the page hides its "i" on a scroll, which can
  // arrive after the mouse is already over the figure: scroll first, then hover until it shows.
  await figure.scrollIntoViewIfNeeded();
  await expect(async () => {
    await figure.hover();
    await frame.getByRole("button", { name: "i" }).click({ timeout: 2000 });
  }).toPass({ timeout: 15000 });
  await expect(frame.getByRole("dialog")).toContainText("sum of q3 sales");
  await expect(frame.getByRole("dialog")).toContainText("q3.csv");

  await page.getByRole("button", { name: "Refresh" }).click();
  await expect(page.getByText(`Refresh the dashboard ${name}.html`)).toBeVisible();
});
