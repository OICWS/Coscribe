import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

test.skip(!process.env.COSCRIBE_E2E_WORKSPACE, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({ viewport: { width: 1600, height: 1000 } });

// A document long enough to scroll inside the panel, with a list near the end to select in.
const FILLER = Array.from({ length: 16 }, (_, i) => `Paragraph ${i} of filler text that makes the document long enough to scroll in the panel.`).join("\\n\\n");
const BODY = `---\\ncoscribe: doc\\n---\\n\\n# Guide\\n\\n${FILLER}\\n\\n## Before\\n\\n- **Distance**: keep it to five to nine km\\n- **Time**: leave at three in the afternoon, golden light at four\\n- **Weather**: no wind is best\\n`;

async function openDoc(page: import("@playwright/test").Page, name: string) {
  await page.goto(freshThreadPath(name));
  await waitForConnected(page);
  await page.locator("textarea").fill(`write it [[stub-tool write_file {"path":"${name}.md","content":"${BODY}"}]] [[stub-say I wrote ${name}.md for you.]]`);
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByTitle(`Open ${name}.md`).click();
  await expect(page.locator(".doc-editor li").nth(1)).toBeAttached();
}

test("the bar over selected words follows the page when it scrolls", async ({ page }) => {
  await openDoc(page, "doc-scroll");
  const item = page.locator(".doc-editor li").nth(1);
  await page.mouse.move(1200, 600);
  await page.mouse.wheel(0, 100000);
  await expect.poll(async () => (await item.boundingBox())?.y ?? 0).toBeGreaterThan(300);
  const at = (await item.boundingBox())!;
  await page.mouse.move(at.x + 120, at.y + at.height / 2);
  await page.mouse.down();
  await page.mouse.move(at.x + 230, at.y + at.height / 2, { steps: 6 });
  await page.mouse.up();
  const ask = page.getByRole("button", { name: "Ask coscribe" });
  await expect(ask).toBeVisible();

  const gap = async () => (await item.boundingBox())!.y - (await ask.boundingBox())!.y;
  const before = await gap();
  await page.mouse.move(1200, 300);
  await page.mouse.wheel(0, -250);
  await expect.poll(async () => Math.abs((await gap()) - before)).toBeLessThan(4);
});

test("the Doc's header has the same comment control as a deck's", async ({ page }) => {
  await openDoc(page, "doc-comment-button");
  await expect(page.getByRole("button", { name: "Comment", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Comment options" }).click();
  await expect(page.getByRole("menuitemradio", { name: "Show all comments" })).toBeVisible();
});

test("a table's number columns line up on the right and its total row is bold, as in Word", async ({ page }) => {
  const name = "doc-table";
  await page.goto(freshThreadPath(name));
  await waitForConnected(page);
  const body = "---\\ncoscribe: doc\\n---\\n\\n# Orders\\n\\n| 渠道 | 订单 |\\n| --- | --- |\\n| 自然搜索 | 1,240 |\\n| 信息流 | 860 |\\n| 合计 | 2,100 |\\n";
  await page.locator("textarea").fill(`write it [[stub-tool write_file {"path":"${name}.md","content":"${body}"}]] [[stub-say done]]`);
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByTitle(`Open ${name}.md`).click();
  const number = page.locator(".doc-editor td", { hasText: "1,240" });
  await expect(number).toHaveCSS("text-align", "right");
  await expect(page.locator(".doc-editor td", { hasText: "合计" })).toHaveCSS("font-weight", "600");
  await expect(page.locator(".doc-editor td", { hasText: "自然搜索" })).not.toHaveCSS("text-align", "right");
});
