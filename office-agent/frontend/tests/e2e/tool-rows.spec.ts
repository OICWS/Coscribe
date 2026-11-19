import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

test("long tool summaries wrap without making the conversation scroll sideways", async ({ page }) => {
  const name = `${"quarterly_export_".repeat(25)}.txt`;
  const path = `pptx-test/${name}`;
  await page.routeWebSocket("**/ws/**", (socket) => {
    const server = socket.connectToServer();
    socket.onMessage((message) => server.send(message));
    server.onMessage((message) => {
      const event = JSON.parse(String(message));
      if (event.type === "history") event.entries = [
        { kind: "user", text: "Read the exported report." },
        { kind: "tool", tool_name: "read_file", arguments: { path }, result: "Report contents", is_error: false },
      ];
      socket.send(JSON.stringify(event));
    });
  });
  await page.goto(freshThreadPath("tool-width"));
  await waitForConnected(page);
  const log = page.getByTestId("chat-log");
  const summary = log.getByRole("button", { name: /^Read / });
  const fits = async () => {
    await expect.poll(() => log.evaluate((el) => el.scrollWidth - el.clientWidth)).toBeLessThanOrEqual(1);
    const lines = await summary.getByText(name, { exact: true }).evaluate((el) => {
      const range = document.createRange();
      range.selectNodeContents(el);
      const bounds = el.closest("button")!.getBoundingClientRect();
      const rects = [...range.getClientRects()];
      return { count: rects.length, inside: rects.every((r) => r.left >= bounds.left - 1 && r.right <= bounds.right + 1) };
    });
    expect(lines.count).toBeGreaterThan(1);
    expect(lines.inside).toBe(true);
  };
  for (const width of [1280, 800]) {
    await page.setViewportSize({ width, height: 860 });
    await fits();
    await page.getByTitle("Plan", { exact: true }).click();
    await fits();
    await log.getByRole("button", { name: "Rewind to here", exact: true }).hover();
    const tip = log.getByRole("tooltip").filter({ hasText: "Takes this message" });
    await expect(tip).toHaveCSS("opacity", "1");
    await fits();
    await summary.click();
    await expect(log.getByText("Report contents", { exact: true })).toBeVisible();
    await fits();
    await summary.click();
    await page.getByTitle("Plan", { exact: true }).click();
  }
});

// An opened tool call reads as "name: value" lines; the JSON is only behind "Raw".
test("an opened tool call shows plain lines, and its JSON only behind Raw", async ({ page }) => {
  await page.goto(freshThreadPath("tool-rows"));
  await waitForConnected(page);
  await page.locator("textarea").fill('list them [[stub-tool list_files {"path":".","pattern":"*.md"}]]');
  await page.keyboard.press("Enter");

  const header = page.getByRole("button", { name: /Listed files/ });
  await header.click();

  await expect(page.getByText("pattern:", { exact: true })).toBeVisible();
  await expect(page.getByText("*.md", { exact: true })).toBeVisible();
  const raw = page.locator("details pre");
  await expect(raw).toBeHidden();

  await page.getByText("Raw", { exact: true }).click();
  await expect(raw).toContainText('"pattern": "*.md"');
});
