import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
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

  // Played on the canvas, the artboard's own page takes the pointer; the others stay editable.
  await page.getByRole("button", { name: "Play", exact: true }).first().click();
  await page.getByRole("menuitem", { name: "Play on canvas" }).click();
  await expect(page.getByTestId("board-home")).toHaveCount(0);
  await expect(page.getByTestId("board-phone")).toBeVisible();
  // Playwright's hit test misreads a frame inside a scaled canvas, so the page's own button is
  // pressed from inside it.
  await expect(page.locator('iframe[title="Home"]')).toHaveCSS("pointer-events", "auto");
  await page.frameLocator('iframe[title="Home"]').getByRole("button", { name: "Start" }).dispatchEvent("click");
  await expect(page.frameLocator('iframe[title="Home"]').getByRole("button", { name: "clicked" })).toBeVisible();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await expect(page.getByTestId("board-home")).toBeVisible();

  // Full screen: one board fills the panel and still works; Edit goes back.
  await page.getByRole("button", { name: "Play full screen" }).click();
  const full = page.getByTestId("board-full-screen");
  await expect(full.locator("iframe")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(full).toHaveCount(0);
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

test("a link from a played artboard to another shows that artboard, played too", async ({ page }) => {
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

  await page.getByRole("button", { name: "Play", exact: true }).first().click();
  await page.getByRole("menuitem", { name: "Play on canvas" }).click();
  await page.frameLocator('iframe[title="Menu"]').getByRole("link", { name: "To checkout" }).dispatchEvent("click");

  const stage = (await page.getByTestId("canvas-stage").boundingBox())!;
  await expect
    .poll(async () => {
      const box = await page.locator('iframe[title="Checkout"]').boundingBox();
      return box ? Math.abs(box.x + box.width / 2 - (stage.x + stage.width / 2)) : Infinity;
    })
    .toBeLessThan(20);
  // The next screen is played now, and the one it came from is back to editing.
  await expect(page.locator('iframe[title="Checkout"]')).toHaveCSS("pointer-events", "auto");
  await expect(page.getByTestId("board-menu")).toBeVisible();
});

const INSPECTED = '{\\"boards\\": [{\\"id\\": \\"card\\", \\"title\\": \\"Card\\", \\"file\\": \\"card.html\\", \\"width\\": 400, \\"height\\": 300}]}';

test("the properties panel shows an artboard's elements and the style of the one picked", async ({ page }) => {
  const name = `inspect-${Math.random().toString(36).slice(2, 8)}`;
  mkdirSync(join(workspace, `${name}.design`), { recursive: true });
  const card =
    "<html><head><style>body{margin:0;font-family:Georgia,serif;color:#123456}.row{display:flex;gap:12px;padding:20px}" +
    "h1{font-size:40px;margin:0}</style></head><body><div class='row'><h1>Hello</h1><p>World</p></div></body></html>";
  writeFileSync(join(workspace, `${name}.design`, "card.html"), card);

  await page.goto(freshThreadPath(name));
  await waitForConnected(page);
  await page.locator("textarea").fill(`draw it [[stub-tool write_file {"path":"${name}.design.json","content":"${INSPECTED}"}]] [[stub-say Done.]]`);
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByTitle(`Open ${name}.design.json`).click();
  await expect(page.frameLocator('iframe[title="Card"]').locator("h1")).toBeVisible();

  await page.getByRole("button", { name: "Properties", exact: true }).click();
  const panel = page.getByRole("complementary", { name: "Properties" });
  await expect(panel.getByText("Select an artboard")).toBeVisible();

  // A click on the board selects it and picks the element under the pointer: the heading, top-left.
  const board = (await page.getByTestId("board-card").boundingBox())!;
  await page.mouse.click(board.x + board.width * 0.12, board.y + board.height * 0.15);
  const tree = panel.getByRole("tree", { name: "Elements" });
  await expect(tree.getByRole("treeitem", { name: /^Row/ })).toBeVisible();
  await expect(tree.getByRole("treeitem", { name: /^Text.*Hello/ })).toHaveAttribute("aria-selected", "true");
  await expect(panel.getByLabel("Size", { exact: true })).toHaveValue("40px");
  await expect(page.getByTestId("inspected-element")).toBeVisible();

  // The tree picks too; the Code tab shows the matching rule and what is inherited.
  await tree.getByRole("treeitem", { name: /^Row/ }).click();
  await panel.getByRole("tab", { name: "Code" }).click();
  await expect(panel.getByText(".row", { exact: true })).toBeVisible();
  await expect(panel.getByText("gap: 12px;")).toBeVisible();
  await expect(panel.getByText("From <body>")).toBeVisible();

  // The Code tab writes any property into the element's own style; undo takes it back.
  const own = panel.getByLabel("This element's style");
  await own.fill("letter-spacing: 2px;");
  await own.press("Control+Enter");
  await expect(page.frameLocator('iframe[title="Card"]').locator(".row")).toHaveCSS("letter-spacing", "2px");
  expect(readFileSync(join(workspace, `${name}.design`, "card.html"), "utf8")).toContain(`<div class='row' style="letter-spacing: 2px">`);
  await panel.getByRole("button", { name: "Undo" }).click();
  await expect(page.frameLocator('iframe[title="Card"]').locator(".row")).toHaveCSS("letter-spacing", "normal");

  // The Properties tab edits: a size and a text are written into the page, which is served anew
  // with the same element picked.
  await panel.getByRole("tab", { name: "Properties" }).click();
  await tree.getByRole("treeitem", { name: /^Text.*Hello/ }).click();
  const size = panel.getByLabel("Size", { exact: true });
  // The pick reaches the panel after the click; a value typed before it would be replaced.
  await expect(tree.getByRole("treeitem", { name: /^Text.*Hello/ })).toHaveAttribute("aria-selected", "true");
  await expect(size).toHaveValue("40px");
  await size.fill("30px");
  await size.press("Enter");
  await expect(page.frameLocator('iframe[title="Card"]').locator("h1")).toHaveCSS("font-size", "30px");
  await expect(panel.getByLabel("Size", { exact: true })).toHaveValue("30px");
  const text = panel.getByLabel("Text", { exact: true });
  await text.fill("Hi there");
  await text.press("Enter");
  await expect(page.frameLocator('iframe[title="Card"]').locator("h1")).toHaveText("Hi there");
  expect(readFileSync(join(workspace, `${name}.design`, "card.html"), "utf8")).toContain('<h1 style="font-size: 30px">Hi there</h1>');

  // Undo takes the edits back one at a time: the button, then Ctrl+Z outside a field.
  const heading = page.frameLocator('iframe[title="Card"]').locator("h1");
  await panel.getByRole("button", { name: "Undo" }).click();
  await expect(heading).toHaveText("Hello");
  await expect(heading).toHaveCSS("font-size", "30px");
  await panel.getByRole("tab", { name: "Properties" }).click();
  await page.keyboard.press("Control+z");
  await expect(heading).toHaveCSS("font-size", "40px");
  await expect(panel.getByRole("button", { name: "Undo" })).toBeDisabled();
  expect(readFileSync(join(workspace, `${name}.design`, "card.html"), "utf8")).toBe(card);

  // Redo does the size again; the steps are the server's, so they are still there after a reload.
  await panel.getByRole("button", { name: "Redo" }).click();
  await expect(heading).toHaveCSS("font-size", "30px");
  await page.reload();
  await page.getByTitle(`Open ${name}.design.json`).click();
  await page.getByRole("button", { name: "Properties", exact: true }).click();
  const again = (await page.getByTestId("board-card").boundingBox())!;
  await page.mouse.click(again.x + again.width * 0.12, again.y + again.height * 0.15);
  await panel.getByRole("button", { name: "Undo" }).click();
  await expect(heading).toHaveCSS("font-size", "40px");
  expect(readFileSync(join(workspace, `${name}.design`, "card.html"), "utf8")).toBe(card);
});

test("a double click on an artboard's text edits it where it is drawn and writes it into the page", async ({ page }) => {
  const name = `intext-${Math.random().toString(36).slice(2, 8)}`;
  mkdirSync(join(workspace, `${name}.design`), { recursive: true });
  const card =
    "<html><head><style>body{margin:0;font-family:Georgia,serif;color:#123456}.row{display:flex;gap:12px;padding:20px}" +
    "h1{font-size:40px;margin:0}</style></head><body><div class='row'><h1>Hello</h1><p>World</p></div></body></html>";
  const file = join(workspace, `${name}.design`, "card.html");
  writeFileSync(file, card);

  await page.goto(freshThreadPath(name));
  await waitForConnected(page);
  await page.locator("textarea").fill(`draw it [[stub-tool write_file {"path":"${name}.design.json","content":"${INSPECTED}"}]] [[stub-say Done.]]`);
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByTitle(`Open ${name}.design.json`).click();
  const heading = page.frameLocator('iframe[title="Card"]').locator("h1");
  await expect(heading).toBeVisible();

  // With the properties panel closed, a double click on the heading opens it and edits the text in
  // place; the page's own copy is hidden meanwhile. Escape leaves the page as it was.
  const board = (await page.getByTestId("board-card").boundingBox())!;
  await page.mouse.dblclick(board.x + board.width * 0.12, board.y + board.height * 0.15);
  const field = page.getByLabel("Edit text", { exact: true });
  await expect(field).toHaveValue("Hello");
  await expect(field).toBeFocused();
  await expect(heading).toHaveCSS("color", "rgba(0, 0, 0, 0)");
  await expect(page.getByRole("complementary", { name: "Properties" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(field).toBeHidden();
  await expect(heading).toHaveCSS("color", "rgb(18, 52, 86)");

  // Typed and Enter: written into the page, which is served anew.
  await page.mouse.dblclick(board.x + board.width * 0.12, board.y + board.height * 0.15);
  await expect(field).toHaveValue("Hello");
  await page.keyboard.type("Good day");
  await page.keyboard.press("Enter");
  await expect(heading).toHaveText("Good day");
  expect(readFileSync(file, "utf8")).toBe(card.replace("<h1>Hello</h1>", "<h1>Good day</h1>"));

  // The row holds elements, not text alone: a double click there only picks it.
  // (Inside its padding, left of the heading; the panel now covers the board's right side.)
  await page.mouse.dblclick(board.x + 8, board.y + 8);
  await expect(page.getByRole("tree", { name: "Elements" }).getByRole("treeitem", { name: /^Row/ })).toHaveAttribute("aria-selected", "true");
  await expect(field).toBeHidden();
});
