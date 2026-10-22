import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// The server's own suggestion needs a model call; the event is injected into the
// real socket so that only the message box's behaviour is under test.
async function openWithSuggestion(page: Page, text: string) {
  let toPage: ((message: string) => void) | null = null;
  const sent: string[] = [];
  await page.routeWebSocket(/\/ws\//, (ws) => {
    const server = ws.connectToServer();
    toPage = (message) => ws.send(message);
    ws.onMessage((message) => {
      sent.push(String(message));
      server.send(message);
    });
  });
  await page.goto(freshThreadPath("suggestion"));
  await waitForConnected(page);
  toPage!(JSON.stringify({ type: "prompt_suggestion", text }));
  return sent;
}

test("Tab puts the suggestion in the box as text to edit", async ({ page }) => {
  await openWithSuggestion(page, "Put the course notes card back");
  const box = page.getByPlaceholder("Put the course notes card back");
  await expect(box).toBeVisible();

  await box.focus();
  await page.keyboard.press("Tab");

  await expect(page.locator("textarea")).toHaveValue("Put the course notes card back");
  await page.keyboard.type(" on page 2");
  await expect(page.locator("textarea")).toHaveValue("Put the course notes card back on page 2");
});

test("Enter sends the suggestion as it is", async ({ page }) => {
  const sent = await openWithSuggestion(page, "Put the course notes card back");
  await page.getByPlaceholder("Put the course notes card back").focus();
  await page.keyboard.press("Enter");

  await expect.poll(() => sent.some((m) => m.includes("Put the course notes card back"))).toBe(true);
});

test("Typing replaces the suggestion", async ({ page }) => {
  await openWithSuggestion(page, "Put the course notes card back");
  await page.getByPlaceholder("Put the course notes card back").focus();
  await page.keyboard.type("x");
  await page.keyboard.press("Backspace");

  await expect(page.getByPlaceholder("Type / for commands")).toBeVisible();
});
