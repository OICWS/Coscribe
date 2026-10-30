import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

const workspace = process.env.COSCRIBE_E2E_WORKSPACE ?? "";
test.skip(!workspace, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({ viewport: { width: 1600, height: 1000 } });

const CANVAS = '{\\"boards\\": [{\\"id\\": \\"home\\", \\"title\\": \\"Home\\", \\"file\\": \\"home.html\\"}, {\\"id\\": \\"phone\\", \\"title\\": \\"Phone\\", \\"file\\": \\"phone.html\\", \\"width\\": 390, \\"height\\": 800}]}';

test("a canvas shows its artboards; a board moves and a note is left, and both are saved", async ({ page }) => {
  const name = `canvas-${Math.random().toString(36).slice(2, 8)}`;
  mkdirSync(join(workspace, `${name}.design`), { recursive: true });
  writeFileSync(join(workspace, `${name}.design`, "home.html"), "<body style='margin:0;font:40px sans-serif'><button onclick=\"this.textContent='clicked'\">Start</button></body>");
  writeFileSync(join(workspace, `${name}.design`, "phone.html"), "<body style='margin:0;background:#eef'>phone</body>");

  await page.goto(freshThreadPath(name));
  await waitForConnected(page);
  await page.locator("textarea").fill(`draw it [[stub-tool write_file {"path":"${name}.design.json","content":"${CANVAS}"}]] [[stub-say Done.]]`);
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByTitle(`Open ${name}.design.json`).click();

  await expect(page.locator('iframe[title="Home"]')).toBeVisible();
  await expect(page.locator('iframe[title="Phone"]')).toBeVisible();

  const board = page.getByTestId("board-phone");
  const at = (await board.boundingBox())!;
  await page.mouse.move(at.x + 20, at.y + 20);
  await page.mouse.down();
  await page.mouse.move(at.x + 20, at.y + 220, { steps: 8 });
  await page.mouse.up();
  const read = async () => (await page.request.get(`/api/threads/${name}/canvas`, { params: { path: `${name}.design.json` } })).json();
  await expect.poll(async () => (await read()).boards[1].y).toBeGreaterThan(100);

  await page.getByRole("button", { name: "Note", exact: true }).click();
  const stage = (await page.getByTestId("canvas-stage").boundingBox())!;
  await page.mouse.click(stage.x + 200, stage.y + stage.height - 120);
  await page.getByLabel("Note text").fill("Bigger title");
  await page.getByRole("button", { name: "Select", exact: true }).click();
  await expect.poll(async () => (await read()).notes.map((n: { text: string }) => n.text)).toEqual(["Bigger title"]);

  // In Play the artboard's own page takes the pointer.
  await page.getByRole("button", { name: "Play" }).click();
  await expect(page.getByTestId("board-home")).toHaveCount(0);
  // Playwright's hit test misreads a frame inside a scaled canvas, so the page's own button is
  // pressed from inside it.
  await expect(page.locator('iframe[title="Home"]')).toHaveCSS("pointer-events", "auto");
  await page.frameLocator('iframe[title="Home"]').getByRole("button", { name: "Start" }).dispatchEvent("click");
  await expect(page.frameLocator('iframe[title="Home"]').getByRole("button", { name: "clicked" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("board-home")).toBeVisible();
});

const THEMED = '{\\"boards\\": [{\\"id\\": \\"card\\", \\"title\\": \\"Card\\", \\"file\\": \\"card.html\\", \\"width\\": 400, \\"height\\": 300}], \\"variables\\": [{\\"name\\": \\"--brand\\", \\"value\\": \\"#2557d6\\", \\"label\\": \\"Brand\\"}]}';

test("a canvas's variables are set from the panel into every artboard, and the boards show dark", async ({ page }) => {
  const name = `themed-${Math.random().toString(36).slice(2, 8)}`;
  mkdirSync(join(workspace, `${name}.design`), { recursive: true });
  const card =
    "<html><head><style>body{margin:0;background:#fff}h1{color:var(--brand)}" +
    "@media (prefers-color-scheme: dark){body{background:rgb(17, 17, 17)}}</style></head><body><h1>Hi</h1></body></html>";
  writeFileSync(join(workspace, `${name}.design`, "card.html"), card);

  await page.goto(freshThreadPath(name));
  await waitForConnected(page);
  await page.locator("textarea").fill(`draw it [[stub-tool write_file {"path":"${name}.design.json","content":"${THEMED}"}]] [[stub-say Done.]]`);
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByTitle(`Open ${name}.design.json`).click();

  const frame = page.frameLocator('iframe[title="Card"]');
  await expect(frame.locator("h1")).toHaveCSS("color", "rgb(37, 87, 214)");

  await page.getByRole("button", { name: "Variables" }).click();
  const brand = page.getByRole("dialog", { name: "Variables" }).getByLabel("Brand", { exact: true });
  await brand.fill("#e0457b");
  await brand.press("Enter");
  await expect(frame.locator("h1")).toHaveCSS("color", "rgb(224, 69, 123)");
  const read = async () => (await page.request.get(`/api/threads/${name}/canvas`, { params: { path: `${name}.design.json` } })).json();
  expect((await read()).variables[0].value).toBe("#e0457b");

  await page.getByRole("button", { name: "Show dark" }).click();
  await expect(frame.locator("body")).toHaveCSS("background-color", "rgb(17, 17, 17)");
});

const LINKED = '{\\"boards\\": [{\\"id\\": \\"menu\\", \\"title\\": \\"Menu\\", \\"file\\": \\"menu.html\\", \\"width\\": 390, \\"height\\": 700}, {\\"id\\": \\"checkout\\", \\"title\\": \\"Checkout\\", \\"file\\": \\"checkout.html\\", \\"width\\": 390, \\"height\\": 700, \\"x\\": 2400, \\"y\\": 900}]}';

test("in Play a link from one artboard to another shows that artboard", async ({ page }) => {
  const name = `linked-${Math.random().toString(36).slice(2, 8)}`;
  mkdirSync(join(workspace, `${name}.design`), { recursive: true });
  writeFileSync(join(workspace, `${name}.design`, "menu.html"), "<body style='margin:0'><a href='checkout.html' style='display:block;font:40px sans-serif'>To checkout</a></body>");
  writeFileSync(join(workspace, `${name}.design`, "checkout.html"), "<body style='margin:0'><a href='menu.html'>Back</a></body>");

  await page.goto(freshThreadPath(name));
  await waitForConnected(page);
  await page.locator("textarea").fill(`draw it [[stub-tool write_file {"path":"${name}.design.json","content":"${LINKED}"}]] [[stub-say Done.]]`);
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByTitle(`Open ${name}.design.json`).click();
  await expect(page.locator('iframe[title="Checkout"]')).toBeAttached();

  await page.getByRole("button", { name: "Play" }).click();
  await page.frameLocator('iframe[title="Menu"]').getByRole("link", { name: "To checkout" }).dispatchEvent("click");

  const stage = (await page.getByTestId("canvas-stage").boundingBox())!;
  await expect
    .poll(async () => {
      const box = await page.locator('iframe[title="Checkout"]').boundingBox();
      return box ? Math.abs(box.x + box.width / 2 - (stage.x + stage.width / 2)) : Infinity;
    })
    .toBeLessThan(20);
  // Still in Play: the next screen takes the pointer too.
  await expect(page.locator('iframe[title="Checkout"]')).toHaveCSS("pointer-events", "auto");
});
