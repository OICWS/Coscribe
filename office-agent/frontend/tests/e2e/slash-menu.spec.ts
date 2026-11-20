import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, newEnvironment, waitForConnected } from "./helpers";

const many = Array.from({ length: 30 }, (_, i) => ({ name: `skill-${String(i).padStart(2, "0")}`, description: `Skill number ${i}` }));

async function serveCommands(page: Page, lists: { name: string; description: string }[][]) {
  let call = 0;
  await page.route("**/api/commands", (route) => route.fulfill({ json: lists[Math.min(call++, lists.length - 1)] }));
}

async function isInView(page: Page, name: string) {
  const item = page.getByRole("option", { name, exact: true });
  const menu = page.getByRole("listbox");
  const [itemBox, menuBox] = [await item.boundingBox(), await menu.boundingBox()];
  return !!itemBox && !!menuBox && itemBox.y >= menuBox.y - 1 && itemBox.y + itemBox.height <= menuBox.y + menuBox.height + 1;
}

test("the highlighted command stays in view as the arrow keys move past the menu's edge", async ({ page }) => {
  await serveCommands(page, [many]);
  await page.goto(freshThreadPath("slash"));
  await waitForConnected(page);
  await page.locator("textarea").fill("/");
  await page.locator("textarea").press("End");
  await expect(page.getByRole("option", { name: "skill-00" })).toBeVisible();

  for (let i = 0; i < 20; i++) await page.keyboard.press("ArrowDown");
  expect(await isInView(page, "skill-20")).toBe(true);

  await page.keyboard.press("ArrowUp");
  for (let i = 0; i < 19; i++) await page.keyboard.press("ArrowUp");
  expect(await isInView(page, "skill-00")).toBe(true);

  // Up from the first wraps to the last.
  await page.keyboard.press("ArrowUp");
  expect(await isInView(page, "skill-29")).toBe(true);
  await page.keyboard.press("Enter");
  await expect(page.locator("textarea")).toHaveValue("/skill-29 ");
});

test("a skill made after the page loaded is offered the next time the menu opens", async ({ page }) => {
  const made = { name: "weekly-report", description: "Write the weekly report" };
  await serveCommands(page, [many.slice(0, 2)]);
  await page.goto(freshThreadPath("slash"));
  await waitForConnected(page);
  const box = page.locator("textarea");
  await box.pressSequentially("/");
  await expect(page.getByRole("option", { name: "skill-01" })).toBeVisible();
  await box.fill("");

  await page.unroute("**/api/commands");
  await serveCommands(page, [[...many.slice(0, 2), made]]);
  await box.pressSequentially("/w");
  await expect(page.getByRole("option", { name: "weekly-report" })).toBeVisible();
});

test("the highlighted command's description shows beside the list", async ({ page }) => {
  await serveCommands(page, [many]);
  await page.goto(freshThreadPath("slash"));
  await waitForConnected(page);
  await page.locator("textarea").fill("/");
  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("tooltip")).toHaveText("Skill number 1");
  const [list, tip] = [await page.getByRole("listbox").boundingBox(), await page.getByRole("tooltip").boundingBox()];
  expect(tip!.x).toBeGreaterThan(list!.x + list!.width);
});

test("/clear archives the conversation and opens a blank one in the same workspace", async ({ page, request }) => {
  await page.goto(freshThreadPath("clear"));
  await waitForConnected(page);
  const workspace = `Clear ${Date.now()}`;
  await newEnvironment(page, workspace);
  const box = page.locator("textarea");
  await box.fill("hello");
  await box.press("Enter");
  await expect(page.getByText("OK").last()).toBeVisible();
  const before = new URL(page.url()).searchParams.get("thread")!;

  await box.fill("/clear");
  await box.press("Enter");
  await expect.poll(() => new URL(page.url()).searchParams.get("thread")).not.toBe(before);
  const threads = (await (await request.get("/api/threads")).json()) as { thread_id: string; archived: boolean }[];
  expect(threads.find((t) => t.thread_id === before)?.archived).toBe(true);
  await expect(page.getByTitle("Choose this conversation's workspace")).toHaveText(workspace);
});

test("during a reply a command waits in the box instead of reaching the model", async ({ page }) => {
  await page.goto(freshThreadPath("slash-reply"));
  await waitForConnected(page);
  const box = page.locator("textarea");
  // The script's approval holds the reply open.
  await box.fill('[[stub-tool run_python_script {"script": "print(1)"}]]');
  await box.press("Enter");
  await expect(page.getByRole("button", { name: "Approve" }).first()).toBeVisible();

  await box.fill("/init");
  await expect(page.getByRole("status").filter({ hasText: "Commands are available once this reply finishes." })).toBeVisible();
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await box.press("Enter");
  await expect(box).toHaveValue("/init");
});

test("the mode button says Switching until the server applies the change", async ({ page }) => {
  let hold = true;
  let release: (() => void) | null = null;
  await page.routeWebSocket(/\/ws\//, (ws) => {
    const server = ws.connectToServer();
    ws.onMessage((message) => {
      if (hold && String(message).includes('"/plan"')) release = () => server.send(message);
      else server.send(message);
    });
  });
  await page.goto(freshThreadPath("slash-mode"));
  await waitForConnected(page);
  const box = page.locator("textarea");
  await box.fill("hello");
  await box.press("Enter");
  const pill = page.locator('button[aria-haspopup="menu"]').filter({ hasText: /^(Auto|Manual|Accept Edits)$/ });
  await pill.click();
  await page.getByRole("menuitemradio", { name: /^Plan/ }).click();
  await expect(page.getByRole("button", { name: "Switching", exact: true })).toBeVisible();

  hold = false;
  release!();
  await expect(page.getByRole("button", { name: "Plan", exact: true })).toBeVisible();
});
