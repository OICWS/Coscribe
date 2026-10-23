import { expect, test } from "@playwright/test";
import { WORKSPACE, clickSlide, freshDeckName, openSectionDeck } from "./slides-helpers";

// The Slides stage's scrollbars. Playwright's Chromium hides scrollbars by default, which would
// hide what these cases are about, so this file runs with them.
test.skip(!WORKSPACE, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({
  viewport: { width: 1600, height: 1200 },
  launchOptions: {
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH ?? "/opt/pw-browsers/chromium",
    ignoreDefaultArgs: ["--hide-scrollbars"],
  },
});

test("an element sticking out of the slide makes the stage scrollable without moving the slide", async ({ page }) => {
  await openSectionDeck(page, freshDeckName());
  const stage = page.locator("[data-slide-stage]");
  const slide = stage.locator("[data-slide]");
  const before = await slide.boundingBox();

  // What a selected element larger than the slide does: its frame reaches past the slide's edges.
  await slide.evaluate((node) => {
    const frame = document.createElement("div");
    frame.style.cssText = "position:absolute;left:0;top:0;width:200%;height:200%;pointer-events:none";
    node.appendChild(frame);
  });
  await expect.poll(() => stage.evaluate((n) => n.scrollWidth > n.clientWidth && n.scrollHeight > n.clientHeight)).toBe(true);

  expect(await slide.boundingBox()).toEqual(before);
});

test("a press on the grey beside the slide clears the selection, a press on the scrollbar does not", async ({ page }) => {
  await openSectionDeck(page, freshDeckName());
  const selection = page.locator("[data-selection]");
  const stage = page.locator("[data-slide-stage]");

  await clickSlide(page, 300, 200);
  await expect(selection).toBeVisible();
  const box = (await stage.boundingBox())!;

  await test.step("the scrollbar is not a click away", async () => {
    await page.mouse.click(box.x + box.width - 4, box.y + box.height / 2);
    await expect(selection).toBeVisible();
  });

  await test.step("the grey beside the slide is", async () => {
    await page.mouse.click(box.x + 20, box.y + box.height - 60);
    await expect(selection).toHaveCount(0);
  });
});
