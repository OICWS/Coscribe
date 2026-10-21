import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// What the server lists comes from what conversations wrote, which a stub model cannot make, so
// the list is the one thing answered here; the page, the sidebar and the navigation are real.
const hoursAgo = (h: number) => new Date(Date.now() - h * 3600e3).toISOString();
const LISTED = [
  { thread_id: "listed-a", path: "q3.pptx", name: "Q3 review", kind: "slides", modified_at: hoursAgo(3), excerpt: null },
  { thread_id: "listed-b", path: "plan.docx", name: "Project plan", kind: "docs", modified_at: hoursAgo(30), excerpt: { heading: "Project plan", text: "Goals and dates." } },
  { thread_id: "listed-b", path: "costs.xlsx", name: "Costs", kind: "sheets", modified_at: hoursAgo(31), excerpt: null },
];

async function openPage(page: Page) {
  await page.route("**/api/artifacts", (route) => route.fulfill({ json: LISTED }));
  await page.addInitScript(() => localStorage.removeItem("coscribe.pinnedArtifacts"));
  await page.goto(freshThreadPath("art"));
  await waitForConnected(page);
  await page.getByTitle("Pin navigation open").click();
  await page.getByRole("button", { name: "Artifacts" }).click();
  await expect(page).toHaveURL(/view=artifacts/);
  await expect(page.getByRole("heading", { name: "Artifacts" })).toBeVisible();
}

test("the sidebar opens the Artifacts page, which lists, searches, filters and pins", async ({ page }) => {
  await openPage(page);
  const cards = page.getByRole("button", { name: /^Open / });
  await expect(cards).toHaveText([/Q3 review/, /Project plan/, /Costs/]);

  await page.getByRole("button", { name: "Search", exact: true }).click();
  await page.getByLabel("Search artifacts").fill("plan");
  await expect(cards).toHaveText([/Project plan/]);
  await page.getByLabel("Search artifacts").press("Escape");
  await expect(cards).toHaveCount(3);

  await page.getByRole("button", { name: "Filter by type" }).click();
  await expect(page.getByRole("menuitemradio", { name: /Sheets/ })).toContainText("1");
  await page.getByRole("menuitemradio", { name: /Sheets/ }).click();
  await expect(cards).toHaveText([/Costs/]);
  await page.getByRole("button", { name: "Filter by type" }).click();
  await page.getByRole("menuitemradio", { name: "All types" }).click();

  // Pinned ones come first, and the Pinned tab keeps only them.
  await page.getByRole("button", { name: "Options for Costs" }).click({ force: true });
  await page.getByRole("menuitem", { name: /^Pin/ }).click();
  await expect(cards.first()).toHaveText(/Costs/);
  await page.getByRole("tab", { name: "Pinned" }).click();
  await expect(cards).toHaveText([/Costs/]);

  // The list layout groups by day, and the choice is kept for the next visit.
  await page.getByRole("tab", { name: "All" }).click();
  await page.getByRole("button", { name: "List view" }).click();
  await expect(page.getByRole("heading", { name: "Pinned" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Today" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("button", { name: "Grid view" })).toBeVisible();
  await page.evaluate(() => localStorage.removeItem("coscribe.artifactsLayout"));
});

test("a card opens its conversation, and a kind starts a new one with its first words typed", async ({ page }) => {
  await openPage(page);
  await page.getByRole("button", { name: /^Open Q3 review/ }).click();
  await expect(page).toHaveURL(/thread=listed-a/);
  await expect(page).not.toHaveURL(/view=artifacts/);

  await page.getByTitle(/navigation/).first().click();
  await page.getByRole("button", { name: "Artifacts" }).click();
  await page.getByRole("button", { name: /^Slides/ }).click();
  await expect(page).not.toHaveURL(/view=artifacts/);
  await expect(page.getByPlaceholder("Type / for commands")).toHaveValue("Make a presentation about ");
});
