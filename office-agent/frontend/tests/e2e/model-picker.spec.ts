import { expect, test, type WebSocketRoute } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

test.use({ viewport: { width: 1100, height: 700 } });

const row = (id: string) => ({ id, name: id, inputs: [], outputs: [], effort_levels: [], context: null, tools: true, kind: "chat", known: false });

test("the model menu opens over the notices above the message box", async ({ page }) => {
  // Enough models that the open menu reaches up past the notice row.
  await page.route("**/api/providers", async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    const response = await route.fetch();
    const providers = await response.json();
    for (const info of Object.values(providers) as { models: unknown[] }[]) {
      info.models = ["fake", "second", "third", "fourth"].map(row);
    }
    await route.fulfill({ response, json: providers });
  });
  let socket: WebSocketRoute | null = null;
  await page.routeWebSocket("**/ws/**", (ws) => {
    const server = ws.connectToServer();
    server.onMessage((message) => ws.send(message));
    socket = ws;
  });

  await page.goto(freshThreadPath("picker"));
  await waitForConnected(page);
  await page.locator("textarea").fill("Reply with just the word ok.");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("model-pill")).toBeEnabled();
  await expect(page.locator("textarea")).toBeEnabled();
  // The stub model does no job worth saving, so the offer comes as the server would send it.
  await expect.poll(() => socket !== null).toBe(true);
  await page.waitForTimeout(1000);
  socket!.send(JSON.stringify({ type: "save_offer", steps: 6, name: "Weekly report" }));
  const save = page.getByRole("button", { name: "Save as workflow" });
  await expect(save).toBeVisible();

  await page.getByTestId("model-pill").click();
  const items = page.getByRole("menu").getByRole("menuitem");
  await expect(items).toHaveCount(4);
  for (const item of await items.all()) {
    const box = (await item.boundingBox())!;
    const covered = await page.evaluate(
      ({ x, y, width, height }) =>
        [0.1, 0.3, 0.5, 0.7, 0.9].filter((f) => document.elementFromPoint(x + width * f, y + height / 2)?.closest("[role=menu]") === null),
      box,
    );
    expect(covered).toEqual([]);
  }
});
