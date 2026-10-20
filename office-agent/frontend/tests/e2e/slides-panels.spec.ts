import { expect, test } from "@playwright/test";
import {
  WORKSPACE,
  clickSlide,
  describeSource,
  dragOnSlide,
  freshDeckName,
  goToSlide,
  openSectionDeck,
  pageSource,
  partsOf,
  pickColour,
  settled,
  until,
  setNumber,
  showProperties,
} from "./slides-helpers";

// The Slides editor's properties panels and containers against the real server: every case
// changes something in the panel or on the stage and checks the page the server saved (or the
// layout it read back), not only what the screen shows. Decks are built from section pages by
// fixtures/build_section_deck.py; slides.spec.ts covers select, move, resize and text.
test.skip(!WORKSPACE, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({ viewport: { width: 1600, height: 1200 } });

const PANELS = "01-panels.html";

test("text panel: a size change shows on the stage, and changing it by hand clears the text style", async ({ page }) => {
  const name = freshDeckName();
  await openSectionDeck(page, name);
  await clickSlide(page, 160 + 450, 140 + 60);
  const panel = await showProperties(page);
  // A text style retags the box (p to h1, ...), so the box is found by its words.
  const text = page.getByText("Panel text", { exact: true });

  await test.step("the size field changes the box on the stage", async () => {
    await expect(text).toHaveCSS("font-size", "32px");
    await setNumber(panel, "Size", 56);
    await expect(text).toHaveCSS("font-size", "56px");
    await expect.poll(() => pageSource(name, PANELS)).toContain("font-size:56px");
  });

  await test.step("a text style names the box in the saved page", async () => {
    await panel.getByRole("button", { name: "Text style" }).click();
    await page.getByRole("menu", { name: "Text style" }).getByRole("menuitemradio").first().click();
    await expect.poll(() => pageSource(name, PANELS)).toMatch(/data-text-style="[\w-]+"/);
  });

  await test.step("a size set by hand takes the box off its style", async () => {
    await setNumber(panel, "Size", 40);
    await expect(text).toHaveCSS("font-size", "40px");
    await expect.poll(() => pageSource(name, PANELS)).not.toContain("data-text-style");
    expect(pageSource(name, PANELS)).toContain("font-size:40px");
  });
});

test("table: a cell is typed into, and rows, columns and the header are set from the panel", async ({ page }) => {
  const name = freshDeckName();
  await openSectionDeck(page, name);
  await clickSlide(page, 385, 500);
  const panel = await showProperties(page);
  const cells = async () => (await describeSource(page, pageSource(name, PANELS))).cells;

  await test.step("a double-click types into a cell and a click away saves it", async () => {
    await clickSlide(page, 385, 500, { dbl: true });
    await page.keyboard.type("Gamma");
    await clickSlide(page, 1700, 1000);
    await expect.poll(cells).toEqual([["Name", "Value"], ["Gamma", "1"], ["Beta", "2"]]);
  });

  await test.step("rows and columns are added from the panel", async () => {
    await clickSlide(page, 385, 500);
    await setNumber(panel, "Rows", 4);
    await expect.poll(async () => (await describeSource(page, pageSource(name, PANELS))).table.rows).toBe(4);
    await setNumber(panel, "Columns", 3);
    await expect.poll(async () => (await describeSource(page, pageSource(name, PANELS))).table.cols).toBe(3);
    const grid = (await cells()).map((row) => row.length);
    expect(grid).toEqual([3, 3, 3, 3]);
    expect((await cells())[1].slice(0, 2)).toEqual(["Gamma", "1"]);
  });

  await test.step("the header toggle turns the header cells on and off", async () => {
    const header = panel.getByRole("checkbox", { name: "Header row" });
    const headers = async () => (await describeSource(page, pageSource(name, PANELS))).table.headers;
    await expect(header).toBeChecked();
    expect(await headers()).toBe(3);
    // Not `uncheck()`: the box is controlled, and shows the new state once the editor publishes it.
    await header.click();
    await expect(header).not.toBeChecked();
    await expect.poll(headers).toBe(0);
    await settled(page);
    await header.click();
    await expect(header).toBeChecked();
    await expect.poll(headers).toBe(3);
  });
});

test("picture and shape: fill and corner radius set in the panel are saved", async ({ page }) => {
  const name = freshDeckName();
  await openSectionDeck(page, name);
  await clickSlide(page, 1250 + 200, 140 + 120);
  const panel = await showProperties(page);
  await expect(panel.getByRole("button", { name: "Background", exact: true })).toContainText("#1A73E8");

  await pickColour(page, panel, "Background", "#E63946");
  await expect.poll(() => pageSource(name, PANELS)).toMatch(/id="card"[^>]*background:#E63946/i);
  await setNumber(panel, "Radius", 60);
  await expect.poll(() => pageSource(name, PANELS)).toMatch(/id="card"[^>]*border-radius:60px/);
  // The panel reads the values back from the saved page.
  await expect(panel.getByRole("button", { name: "Background", exact: true })).toContainText("#E63946");
  await expect(panel.getByRole("textbox", { name: "Radius" })).toHaveValue("60");
});

test("container: a row of two texts, a gap from the panel, and deleting one gives its room to the other", async ({ page }) => {
  const name = freshDeckName();
  await openSectionDeck(page, name);
  await goToSlide(page, 2);
  await page.getByRole("button", { name: "Insert a shape" }).click();
  await page.getByRole("menuitem", { name: "Row container" }).click();
  const panel = await showProperties(page);
  const laid = async () => {
    const read = await partsOf(page, name, 1);
    // The container, then the two texts it holds, after the heading.
    return read && read.parts.length === 4 ? read.parts.slice(1).map((p) => p.box as number[]) : null;
  };
  const laidOut = async () => (await until(laid)) as number[][];

  await test.step("the stage shows the two texts side by side", async () => {
    const [row, one, two] = await laidOut();
    expect(one[1]).toBe(two[1]);
    expect(one[0] + one[2]).toBeLessThanOrEqual(two[0]);
    expect(one[2]).toBeCloseTo(two[2], 0);
    expect(one[0]).toBeGreaterThanOrEqual(row[0]);
    expect(two[0] + two[2]).toBeLessThanOrEqual(row[0] + row[2]);
    const texts = page.getByText("Text", { exact: true });
    await expect(texts).toHaveCount(2);
    const [a, b] = await Promise.all([texts.nth(0).boundingBox(), texts.nth(1).boundingBox()]);
    expect(a && b && a.x + a.width <= b.x + 1).toBe(true);
  });

  await test.step("a gap set in the panel moves them apart", async () => {
    const [, one, two] = await laidOut();
    const before = two[0] - (one[0] + one[2]);
    expect(before).toBe(24);
    await setNumber(panel, "Gap", 100);
    await expect.poll(async () => {
      const now = await laid();
      return now ? now[2][0] - (now[1][0] + now[1][2]) : null;
    }).toBe(100);
    expect(pageSource(name, "02-empty.html")).toContain("gap:100px");
  });

  await test.step("deleting one text gives the other the whole row", async () => {
    const [row, one] = await laidOut();
    await clickSlide(page, one[0] + one[2] / 2, one[1] + one[3] / 2);
    await page.keyboard.press("Delete");
    const read = await until(async () => {
      const found = await partsOf(page, name, 1);
      return found?.parts.length === 3 ? found : null;
    });
    const [container, rest] = read.parts.slice(1).map((p) => p.box as number[]);
    expect(container).toEqual(row);
    // Padding is 24px each side of the container.
    expect(rest[2]).toBeCloseTo(row[2] - 48, 0);
  });
});

test("drag: a text box dropped on a container becomes its child, and dragged out it leaves", async ({ page }) => {
  const name = freshDeckName();
  await openSectionDeck(page, name);
  await goToSlide(page, 3);
  const file = "03-row.html";
  const stack = async () => (await describeSource(page, pageSource(name, file))).stack;
  const boxOf = async (index: number) => (await partsOf(page, name, 2))?.parts[index].box as number[];
  await expect.poll(async () => (await partsOf(page, name, 2))?.parts.length).toBe(4);

  await test.step("dropped to the right of the two texts it joins them as the third", async () => {
    // parts: the row, first, second, loose.
    await clickSlide(page, 400, 840);
    const row = await boxOf(0);
    await dragOnSlide(page, [400, 840], [row[0] + row[2] - 60, row[1] + row[3] / 2]);
    await expect.poll(stack).toEqual(["first", "second", "loose"]);
    expect((await describeSource(page, pageSource(name, file))).sectionChildren).toEqual(["row"]);
  });

  await test.step("dragged out of the container it is back on the slide with a place of its own", async () => {
    await expect.poll(async () => (await partsOf(page, name, 2))?.parts.length).toBe(4);
    const loose = await boxOf(3);
    await dragOnSlide(page, [loose[0] + loose[2] / 2, loose[1] + loose[3] / 2], [900, 800]);
    await expect.poll(stack).toEqual(["first", "second"]);
    const source = pageSource(name, file);
    const [style] = /<p id="loose" style="([^"]*)"/.exec(source)?.slice(1) ?? [];
    expect(style).toMatch(/(^|;)left:\d+px/);
    expect(style).toMatch(/(^|;)top:\d+px/);
    expect(style).not.toContain("flex-grow");
  });
});

test("bring forward on a child of a container swaps it with its sibling", async ({ page }) => {
  const name = freshDeckName();
  await openSectionDeck(page, name);
  await goToSlide(page, 3);
  await expect.poll(async () => (await partsOf(page, name, 2))?.parts.length).toBe(4);
  const [, first, second] = (await partsOf(page, name, 2))?.parts.map((p) => p.box as number[]) ?? [];
  expect(first[0]).toBeLessThan(second[0]);
  await settled(page);

  await clickSlide(page, first[0] + first[2] / 2, first[1] + first[3] / 2);
  await page.getByRole("button", { name: "More" }).click();
  await page.getByRole("menuitem", { name: /^Bring forward/ }).click();

  await expect.poll(async () => (await describeSource(page, pageSource(name, "03-row.html"))).stack).toEqual(["second", "first"]);
  // The layout puts "First" where "Second" was, and "Second" where "First" was.
  await expect.poll(async () => (await partsOf(page, name, 2))?.parts[2].box?.[0]).toBe(second[0]);
  expect((await partsOf(page, name, 2))?.parts[1].box?.[0]).toBe(first[0]);
});

test("the comments card closes on a click outside and on Escape", async ({ page }) => {
  const name = freshDeckName();
  await openSectionDeck(page, name);
  const comment = page.getByRole("textbox", { name: "Comment" });
  const startComment = async () => {
    // Escape also ends commenting, a click away does not.
    const toggle = page.getByRole("button", { name: "Comment", exact: true });
    if ((await toggle.getAttribute("aria-pressed")) !== "true") await toggle.click();
    await page.getByLabel("Click to comment").click({ position: { x: 300, y: 200 } });
    await expect(comment).toBeVisible();
  };

  await test.step("a new comment's card", async () => {
    await startComment();
    await page.mouse.click(5, 5);
    await expect(comment).toBeHidden();
    await startComment();
    await page.keyboard.press("Escape");
    await expect(comment).toBeHidden();
  });

  await test.step("an existing comment's card", async () => {
    await startComment();
    await comment.fill("Look at this");
    await page.getByRole("button", { name: "Post comment" }).click();
    const pin = page.getByLabel(/^Comment by .*Look at this/);
    const reply = page.getByRole("textbox", { name: "Reply" });
    await pin.click();
    await expect(reply).toBeVisible();
    await page.mouse.click(5, 5);
    await expect(reply).toBeHidden();
    await pin.click();
    await expect(reply).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(reply).toBeHidden();
  });
});
