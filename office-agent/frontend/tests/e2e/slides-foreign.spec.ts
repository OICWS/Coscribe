import { execFileSync } from "node:child_process";
import { expect, test, type Page } from "@playwright/test";
import { freshDeckName, WORKSPACE } from "./slides-helpers";
import { freshThreadPath, waitForConnected } from "./helpers";

// A presentation coscribe did not build is shown, not edited: the controls that change a deck are
// left out, and a slide the server cannot draw says so instead of showing a broken picture.
test.skip(!WORKSPACE, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({ viewport: { width: 1600, height: 1000 } });

const SLIDE = { kind: "page", notes: "", transition: null, background: null, elements: [] };
const SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080"><rect width="1920" height="1080" fill="#e8eefc"/></svg>`;

/** What the server answers for a deck coscribe did not build; the e2e runner has no office program to draw one. */
async function answerAsForeign(page: Page, drawable: boolean) {
  await page.route(/\/slides\?path=/, (route) =>
    route.fulfill({
      json: { title: "Foreign", folder: "", changed: false, readOnly: true, slides: [{ ...SLIDE, name: "slide 1" }, { ...SLIDE, name: "slide 2" }] },
    }),
  );
  await page.route(/\/slides\/\d+\/svg/, (route) =>
    drawable ? route.fulfill({ body: SVG, contentType: "image/svg+xml" }) : route.fulfill({ status: 500, json: { error: "no office program" } }),
  );
}

async function openForeignDeck(page: Page, name: string, drawable = true) {
  execFileSync("python", [
    "-c",
    `from pptx import Presentation
p = Presentation()
for title in ("First", "Second"):
    slide = p.slides.add_slide(p.slide_layouts[5])
    slide.shapes.title.text = title
p.save(r"${WORKSPACE}/${name}.pptx")`,
  ]);
  await answerAsForeign(page, drawable);
  await page.goto(freshThreadPath("foreign"));
  await waitForConnected(page);
  await page.locator("textarea").fill(`open it [[stub-tool read_pptx {"path":"${name}.pptx"}]]`);
  await page.keyboard.press("Enter");
  await page.getByTitle("Show task details").click();
  await page.getByRole("button", { name: `${name}.pptx Read` }).click();
  await page.getByRole("button", { name: "Expand Viewer" }).click();
  await expect(page.getByRole("button", { name: "Slide 1" }).first()).toBeVisible();
}

test("a deck coscribe did not build has no controls that change it", async ({ page }) => {
  await openForeignDeck(page, freshDeckName());

  await expect(page.getByText(/Read-only: coscribe did not build this presentation/i)).toBeVisible();
  for (const name of ["New slide", "Comment", "Comment options", "Properties panel"]) {
    await expect(page.getByRole("button", { name, exact: true })).toHaveCount(0);
  }
  await expect(page.getByRole("button", { name: "Edit the slide" })).toHaveCount(0);

  // A right-click on a thumbnail offers no slide menu.
  await page.getByRole("button", { name: "Slide 2" }).click({ button: "right" });
  await expect(page.getByRole("menu", { name: "Slide" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Slide 2" })).toHaveAttribute("draggable", "false");
});

test("a slide that cannot be drawn says so instead of showing a broken picture", async ({ page }) => {
  await openForeignDeck(page, freshDeckName(), false);

  await expect(page.getByText("This slide can't be shown here").first()).toBeVisible();
});
