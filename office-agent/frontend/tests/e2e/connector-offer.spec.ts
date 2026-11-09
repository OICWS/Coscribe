import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// Decision 0041: the model offers a catalog connector on a card; only the person connects it.
async function offerNotion(page: Page, prefix: string) {
  await page.goto(freshThreadPath(prefix));
  await waitForConnected(page);
  await page
    .locator("textarea")
    .fill(
      'summarize my plan [[stub-tool suggest_connector {"name":"notion","reason":"To read your project plan."}]] [[stub-say Connect Notion and I will read it.]]',
    );
  await page.keyboard.press("Enter");
  const card = page.getByTestId("connector-offer");
  await expect(card).toContainText("Connect Notion?");
  await expect(card).toContainText("To read your project plan.");
  await expect(page.getByText("Connect Notion and I will read it.", { exact: true })).toBeVisible();
  return card;
}

test("Not now carries the conversation on without the connector", async ({ page }) => {
  const card = await offerNotion(page, "offer-not-now");
  await card.getByRole("button", { name: "Not now" }).click();
  await expect(page.getByText("Not now. Please continue without Notion.", { exact: true })).toBeVisible();
  await expect(card.getByRole("button", { name: "Not now" })).toBeHidden();
  await expect(card.getByRole("button", { name: "Connect" })).toBeVisible();
});

test("Connect adds it as Settings does and continues once it is connected", async ({ page }) => {
  let added = false;
  // No real sign-in here: the add and the server list answer as a connected Notion would.
  await page.route("**/api/mcp/servers", async (route) => {
    if (route.request().method() === "POST") {
      added = true;
      expect(route.request().postDataJSON()).toMatchObject({
        name: "notion",
        server_url: "https://mcp.notion.com/mcp",
        auth: "oauth",
      });
      await route.fulfill({ json: { rejected: {}, connected: true, error: null } });
      return;
    }
    await route.fulfill({
      json: added ? { notion: { server_url: "https://mcp.notion.com/mcp", auth: "oauth", connected: true } } : {},
    });
  });
  const card = await offerNotion(page, "offer-connect");
  await card.getByRole("button", { name: "Connect" }).click();
  await expect(card).toContainText("Connected");
  await expect(page.getByText("I connected Notion. Please continue.", { exact: true })).toBeVisible();
  await expect(card.getByRole("button", { name: "Continue" })).toBeHidden();
});

test("an entry that needs a one-time setup opens its page in Settings", async ({ page }) => {
  await page.goto(freshThreadPath("offer-setup"));
  await waitForConnected(page);
  await page
    .locator("textarea")
    .fill('draft it [[stub-tool suggest_connector {"name":"gmail","reason":"To draft the reply."}]]');
  await page.keyboard.press("Enter");
  const card = page.getByTestId("connector-offer");
  await card.getByRole("button", { name: "Set up in Settings" }).click();
  await expect(page.getByRole("heading", { name: "Set up Gmail" })).toBeVisible();
});
