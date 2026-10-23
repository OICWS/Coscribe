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
  const box = page.getByPlaceholder("What should this deck be about?");
  await expect(box).toHaveValue("");
  await expect(page.getByRole("button", { name: "Slides mode" })).toBeVisible();

  // The kind is only a request: its menu removes it, and the ordinary box is back.
  await page.getByRole("button", { name: "Slides mode" }).click();
  await page.getByRole("menuitem", { name: "Remove deck" }).click();
  await expect(page.getByPlaceholder("Type / for commands")).toBeVisible();
});

test("the first message of a kind is sent as what to make, and the replayed history shows only what was typed", async ({ page }) => {
  await openPage(page);
  await page.getByRole("button", { name: /^Docs/ }).click();
  await page.getByPlaceholder("What should this document be about?").fill("a one-page note on tea");
  await page.keyboard.press("Enter");
  await expect(page.getByText("a one-page note on tea")).toBeVisible();
  await expect(page.getByRole("button", { name: "Docs mode" })).toHaveCount(0);
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
    await expect(page.getByRole("button", { name: "Choose design system…" })).toBeVisible();
    // The message box is laid out again as the new conversation loads, which closes an open menu: open it until it holds.
    await expect(async () => {
      if (!(await page.getByRole("menuitem", { name: "Manage design systems" }).isVisible())) await page.getByRole("button", { name: "Choose design system…" }).click();
      await expect(page.getByRole("menuitemradio", { name: "Chip test" })).toBeVisible({ timeout: 2000 });
    }).toPass({ timeout: 20_000 });
    await expect(page.getByRole("menuitem", { name: "Manage design systems" })).toBeVisible();
    await page.getByRole("menuitemradio", { name: "Chip test" }).click();
    await expect(page.getByRole("button", { name: "Chip test" })).toBeVisible();

    await page.getByPlaceholder("What should this deck be about?").fill("a deck about tea");
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
  await expect(page.getByRole("button", { name: "Docs mode" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Choose design system…" })).toHaveCount(0);
});

// The message box is laid out again as the new conversation loads, which closes an open menu: open it until the item holds.
async function chooseFromDesignMenu(page: Page, item: string) {
  await expect(async () => {
    if (!(await page.getByRole("menuitem", { name: item }).isVisible())) await page.getByRole("button", { name: "Choose design system…" }).click();
    await expect(page.getByRole("menuitem", { name: item })).toBeVisible({ timeout: 2000 });
  }).toPass({ timeout: 20_000 });
  await page.getByRole("menuitem", { name: item }).click();
}

test("the design-system menu leads to the page that manages them, or to making a new one", async ({ page }) => {
  await openPage(page);
  await page.getByRole("button", { name: /^Slides/ }).click();
  await waitForConnected(page);
  await expect(page.getByPlaceholder("What should this deck be about?")).toBeVisible();
  await chooseFromDesignMenu(page, "Manage design systems");
  await expect(page.getByRole("button", { name: "New design system" })).toBeVisible();
  await expect(page.getByLabel("New design system name")).toHaveCount(0);
  await page.getByRole("button", { name: "Close settings" }).click();

  await chooseFromDesignMenu(page, "Make a new design system first");
  await expect(page.getByLabel("New design system name")).toBeVisible();
});

test("a design system is a card of its own: it opens its editor, and its menu renames, copies, pins and deletes", async ({ page }) => {
  const name = `Brand ${Math.random().toString(36).slice(2, 7)}`;
  const made = (await (await page.request.post("/api/design-systems", { data: { name } })).json()) as { id: string };
  const listed = async () => ((await (await page.request.get("/api/design-systems")).json()) as { id: string; name: string }[]).map((s) => s.name);
  try {
    await openPage(page);
    const card = page.getByRole("button", { name: `Open ${name}` });
    await expect(card).toBeVisible();

    await card.click();
    await expect(page.getByRole("button", { name: "Back to design systems" })).toBeVisible();
    await expect(page.getByLabel("Overview", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Close settings" }).click();

    const options = async (item: string) => {
      await expect(async () => {
        await page.getByRole("button", { name: `Options for ${item}` }).click({ force: true });
        await expect(page.getByRole("menu", { name: `Options for ${item}` })).toBeVisible({ timeout: 2000 });
      }).toPass({ timeout: 15000 });
    };
    await options(name);
    const menu = page.getByRole("menu", { name: `Options for ${name}` });
    await expect(menu).toContainText("Design system");
    await expect(menu.getByRole("menuitem", { name: "Show in folder" })).toHaveCount(0);
    await menu.getByRole("menuitem", { name: "Pin" }).click();
    await options(name);
    await expect(page.getByRole("menuitem", { name: "Unpin" })).toBeVisible();
    await page.getByRole("menuitem", { name: "Duplicate" }).click();
    await expect.poll(listed).toContain(`${name} copy`);

    await page.reload();
    await expect(page.getByRole("heading", { name: "Artifacts" })).toBeVisible();
    await options(`${name} copy`);
    await page.getByRole("menuitem", { name: "Rename" }).click();
    await page.getByLabel("Name").fill(`${name} v2`);
    await page.getByRole("button", { name: "Rename", exact: true }).click();
    await expect.poll(listed).toContain(`${name} v2`);

    await options(`${name} v2`);
    await page.getByRole("menuitem", { name: "Delete" }).click();
    await expect(page.getByText("Decks already made from it keep their own copy")).toBeVisible();
    await page.getByRole("button", { name: "Delete", exact: true }).click();
    await expect.poll(listed).not.toContain(`${name} v2`);
  } finally {
    for (const system of (await (await page.request.get("/api/design-systems")).json()) as { id: string; name: string }[]) {
      if (system.name.startsWith(name) || system.id === made.id) await page.request.delete(`/api/design-systems/${system.id}`, { timeout: 5000 });
    }
  }
});

test("the design-system tile opens Settings on its new-system form", async ({ page }) => {
  await openPage(page);
  await page.getByRole("button", { name: /^Design system/ }).click();
  await expect(page.getByLabel("New design system name")).toBeVisible();
});
