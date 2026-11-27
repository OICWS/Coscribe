import { expect, test } from "@playwright/test";
import { WORKSPACE, clickSlide, freshDeckName, openSectionDeck } from "./slides-helpers";

// The Slides stage's scrollbars, and the deck presented full screen. Playwright's Chromium hides
// scrollbars by default, which would hide what the stage cases are about, so this file runs with them.
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

test("presented full screen, the slide takes the whole height and the bar only shows near the bottom", async ({ page }) => {
  await openSectionDeck(page, freshDeckName());
  // A screen wider than the deck, so the slide's height is what the bar would take from.
  await page.setViewportSize({ width: 1600, height: 800 });
  await page.getByRole("button", { name: "Present", exact: true }).click();
  await page.getByRole("menuitem", { name: "Present", exact: true }).click();
  const presenter = page.getByRole("dialog", { name: "Presenting" });
  await expect(presenter).toBeFocused();
  await page.keyboard.press("f");
  await expect.poll(() => page.evaluate(() => document.fullscreenElement?.getAttribute("aria-label"))).toBe("Presenting");

  const bar = presenter.locator("[data-presenter-bar]");
  await page.mouse.move(800, 300);
  await expect(bar).toHaveCSS("opacity", "0");
  const slide = await presenter.locator("img").boundingBox();
  expect(slide?.height).toBe(800);

  await page.mouse.move(800, 780);
  await expect(bar).toHaveCSS("opacity", "1");
  await bar.getByRole("button", { name: "Next slide" }).click();
  await expect(bar).toContainText("2 /");
  expect((await presenter.locator("img").boundingBox())?.height).toBe(800);

  // The button just clicked keeps the focus, but only a keyboard focus keeps the bar up.
  await page.mouse.move(800, 300);
  await expect(bar).toHaveCSS("opacity", "0");
  await page.keyboard.press("Tab");
  await expect(bar).toHaveCSS("opacity", "1");

  // Out of full screen the bar sits under the slide again.
  await page.keyboard.press("f");
  await expect.poll(() => page.evaluate(() => document.fullscreenElement)).toBeNull();
  await expect(bar).toHaveCount(0);
  await expect(presenter.getByRole("button", { name: "Next slide" })).toBeVisible();
});
