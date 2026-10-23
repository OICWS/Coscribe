import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// What the server lists comes from what conversations wrote, which a stub model cannot make, so
// the list is the one thing answered here; the page, the sidebar and the navigation are real.
const hoursAgo = (h: number) => new Date(Date.now() - h * 3600e3).toISOString();
// Earlier today whatever the hour: three hours ago is yesterday in the first hours after midnight.
const earlierToday = () => {
  const midnight = new Date();
  midnight.setHours(0, 0, 0, 0);
  return new Date(Math.max(Date.now() - 3 * 3600e3, midnight.getTime())).toISOString();
};
const LISTED = [
  { id: "a1", path: "q3.pptx", location: "/w/q3.pptx", name: "Q3 review", kind: "slides", modified_at: earlierToday(), excerpt: null },
  { id: "b1", path: "plan.docx", location: "/w/plan.docx", name: "Project plan", kind: "docs", modified_at: hoursAgo(30), excerpt: { heading: "Project plan", text: "Goals and dates." } },
  { id: "c1", path: "costs.xlsx", location: "/w/costs.xlsx", name: "Costs", kind: "sheets", modified_at: hoursAgo(31), excerpt: null },
];

async function openPage(page: Page) {
  await page.route("**/api/artifacts", (route) => route.fulfill({ json: LISTED }));
  await page.route("**/api/artifacts/*/open", (route) => route.fulfill({ json: { thread_id: "listed-a", path: "q3.pptx" } }));
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

test("a card opens its conversation, and a kind starts a new one with a chip and a prompt for it", async ({ page }) => {
  await openPage(page);
  await page.getByRole("button", { name: /^Open Q3 review/ }).click();
  await expect(page).toHaveURL(/thread=listed-a/);
  await expect(page).not.toHaveURL(/view=artifacts/);

  await page.getByTitle(/navigation/).first().click();
  await page.getByRole("button", { name: "Artifacts" }).click();
  await page.getByRole("button", { name: /^Slides/ }).click();
  await expect(page).not.toHaveURL(/view=artifacts/);
  const box = page.getByPlaceholder("Describe the presentation you want");
  await expect(box).toHaveValue("");
  await expect(page.getByRole("button", { name: "Remove Slides mode" })).toBeVisible();

  // The kind is only a request: the chip goes away, and the ordinary box is back.
  await page.getByRole("button", { name: "Remove Slides mode" }).click();
  await expect(page.getByPlaceholder("Type / for commands")).toBeVisible();
});

test("the first message of a kind is sent as what to make, and the replayed history shows only what was typed", async ({ page }) => {
  await openPage(page);
  await page.getByRole("button", { name: /^Docs/ }).click();
  await page.getByPlaceholder("Describe the document you want").fill("a one-page note on tea");
  await page.keyboard.press("Enter");
  await expect(page.getByText("a one-page note on tea")).toBeVisible();
  await expect(page.getByRole("button", { name: "Remove Docs mode" })).toHaveCount(0);
  await page.reload();
  await expect(page.getByText("a one-page note on tea")).toBeVisible();
  await expect(page.getByText("starting a Docs artifact")).toHaveCount(0);
});

test("a card's menu renames, copies and deletes through the app's own dialogs", async ({ page }) => {
  const calls: string[] = [];
  await page.route("**/api/artifacts/b1/rename", (route) => {
    calls.push(`rename ${route.request().postData()}`);
    return route.fulfill({ json: { ...LISTED[1], name: "Roadmap", path: "Roadmap.docx" } });
  });
  await page.route("**/api/artifacts/b1", (route) => {
    calls.push(route.request().method());
    return route.fulfill({ json: { deleted: "b1" } });
  });
  await openPage(page);

  await page.getByRole("button", { name: "Options for Project plan" }).click({ force: true });
  const menu = page.getByRole("menu", { name: "Options for Project plan" });
  await expect(menu).toContainText("Document");
  await expect(menu.getByRole("menuitem", { name: "Open in Word" })).toBeVisible();
  await menu.getByRole("menuitem", { name: "Rename" }).click();
  await page.getByLabel("Name").fill("Roadmap");
  await page.getByRole("button", { name: "Rename", exact: true }).click();
  await expect.poll(() => calls).toContain('rename {"name":"Roadmap"}');

  // The rename dialog is still handing focus back; a click that lands in that moment closes the menu again.
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(async () => {
    await page.getByRole("button", { name: "Options for Project plan" }).click({ force: true });
    await expect(page.getByRole("menuitem", { name: "Delete" })).toBeVisible({ timeout: 2000 });
  }).toPass({ timeout: 15000 });
  await page.getByRole("menuitem", { name: "Delete" }).click();
  await expect(page.getByText("moves Project plan to the Recycle Bin")).toBeVisible();
  await page.getByRole("button", { name: "Delete", exact: true }).click();
  await expect.poll(() => calls).toContain("DELETE");
});

test("a Slides start offers the design-system library, and the first message names the one chosen", async ({ page }) => {
  const sent: string[] = [];
  page.on("websocket", (socket) => socket.on("framesent", (frame) => sent.push(String(frame.payload))));
  const made = await page.request.post("/api/design-systems", { data: { name: "Chip test" } });
  const system = (await made.json()) as { id: string };
  try {
    await openPage(page);
    await page.getByRole("button", { name: /^Slides/ }).click();
    await waitForConnected(page);
    await expect(page.getByRole("button", { name: /^Design system: none/ })).toBeVisible();
    // The message box is laid out again as the new conversation loads, which closes an open menu: open it until it holds.
    await expect(async () => {
      if (!(await page.getByRole("menuitem", { name: /design system/i }).isVisible())) await page.getByRole("button", { name: /^Design system: none/ }).click();
      await expect(page.getByRole("menuitemradio", { name: "Chip test" })).toBeVisible({ timeout: 2000 });
    }).toPass({ timeout: 20_000 });
    await expect(page.getByRole("menuitem", { name: /Manage design systems/ })).toBeVisible();
    await page.getByRole("menuitemradio", { name: "Chip test" }).click();
    await expect(page.getByRole("button", { name: "Design system: Chip test" })).toBeVisible();

    await page.getByPlaceholder("Describe the presentation you want").fill("a deck about tea");
    await page.keyboard.press("Enter");
    await expect(page.getByText("a deck about tea")).toBeVisible();
    await expect.poll(() => sent.some((payload) => payload.includes('"design_system"') && payload.includes(system.id) && payload.includes('"artifact":"slides"'))).toBe(true);
  } finally {
    await page.request.delete(`/api/design-systems/${system.id}`, { timeout: 5000 });
  }
});

test("only a Slides start offers a design system", async ({ page }) => {
  await openPage(page);
  await page.getByRole("button", { name: /^Docs/ }).click();
  await expect(page.getByRole("button", { name: "Remove Docs mode" })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Design system/ })).toHaveCount(0);
});

test("the design-system menu leads to the page that manages them", async ({ page }) => {
  await openPage(page);
  await page.getByRole("button", { name: /^Slides/ }).click();
  await waitForConnected(page);
  await page.getByRole("button", { name: /^Design system: none/ }).click();
  await page.getByRole("menuitem", { name: /design system/i }).click();
  await expect(page.getByRole("button", { name: "New design system" })).toBeVisible();
});
