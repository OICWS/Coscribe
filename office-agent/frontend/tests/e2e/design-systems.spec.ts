import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// Settings > Design systems: make one from the blank form, edit and save it, see it in the list,
// then delete it.
test("a design system is made, edited, saved and deleted from Settings", async ({ page }) => {
  const name = `Acme ${Math.random().toString(36).slice(2, 7)}`;
  await page.goto(freshThreadPath("design-systems"));
  await waitForConnected(page);
  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("button", { name: "Design systems" }).click();

  await page.getByRole("button", { name: "New design system" }).click();
  await page.getByLabel("New design system name").fill(name);
  await page.getByRole("button", { name: "Create" }).click();

  // The new system opens on its Overview with the starting colors under Colors.
  const save = page.getByRole("button", { name: "Save", exact: true });
  await expect(save).toBeDisabled();
  await page.getByLabel("Overview", { exact: true }).fill("Calm and technical.");
  await expect(save).toBeEnabled();
  await page.getByRole("button", { name: "Colors", exact: true }).click();
  await expect(page.getByLabel("Color name").first()).toHaveValue("Background");
  await page.getByRole("button", { name: "Add color" }).click();
  await page.getByLabel("Color name").last().fill("Brand");
  await page.getByLabel("Color value").last().fill("#112233");
  await save.click();
  await expect(save).toBeDisabled();

  // A bad value is refused with the server's reason and keeps what was typed.
  await page.getByLabel("Color value").last().fill("blue");
  await save.click();
  await expect(page.getByRole("alert")).toContainText("not a color");
  await page.getByLabel("Color value").last().fill("#445566");
  await save.click();
  await expect(save).toBeDisabled();

  await page.getByRole("button", { name: "Back to design systems" }).click();
  await expect(page.getByText(name, { exact: true })).toBeVisible();
  const row = page.getByRole("listitem").filter({ hasText: name });
  await row.getByRole("button", { name: "Edit" }).click();
  await page.getByRole("button", { name: "Colors", exact: true }).click();
  await expect(page.getByLabel("Color value").last()).toHaveValue("#445566");
  await page.getByRole("button", { name: "Back to design systems" }).click();

  await row.getByRole("button", { name: "Delete" }).click();
  // The confirmation is the last Delete on the page.
  await page.getByRole("button", { name: "Delete", exact: true }).last().click();
  await expect(page.getByText(name, { exact: true })).toHaveCount(0);
});

test("Describe it in Settings closes it and starts the conversation that makes a design system", async ({ page }) => {
  await page.goto(freshThreadPath("design-systems-describe"));
  await waitForConnected(page);
  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("button", { name: "Design systems" }).click();

  await page.getByRole("button", { name: "Describe it" }).click();

  await expect(page.getByRole("button", { name: "Close settings" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Design system mode" })).toBeVisible();
  await expect(page.getByPlaceholder("Describe the brand or the look you want…")).toBeVisible();
});

// A system's Assets: a logo added from a file is kept at once, drawn, given a kind and a note, and
// still there when the system is opened again.
test("a design system keeps a logo with a note on when to use it", async ({ page }) => {
  const name = `Brand ${Math.random().toString(36).slice(2, 7)}`;
  await page.goto(freshThreadPath("design-assets"));
  await waitForConnected(page);
  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("button", { name: "Design systems" }).click();
  await page.getByRole("button", { name: "New design system" }).click();
  await page.getByLabel("New design system name").fill(name);
  await page.getByRole("button", { name: "Create" }).click();

  await page.getByRole("button", { name: "Assets", exact: true }).click();
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 40"><rect width="120" height="40" fill="#0F766E"/></svg>';
  await page.getByTestId("asset-file").setInputFiles({ name: "acme-logo.svg", mimeType: "image/svg+xml", buffer: Buffer.from(svg) });
  await expect(page.getByLabel("Picture name")).toHaveValue("acme-logo");
  // Drawn from the server: the picture loads (an SVG sized by its viewBox has no fixed natural width).
  const logo = page.getByRole("img", { name: "acme-logo" });
  await expect.poll(() => logo.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  await expect(page.getByText("120×40")).toBeVisible();
  await page.getByLabel("Kind").selectOption("icon");
  const note = page.getByLabel("When to use it");
  await note.fill("On dark backgrounds");
  await note.press("Enter");

  // Not a picture: refused with the reason, nothing added.
  await page.getByTestId("asset-file").setInputFiles({ name: "notes.png", mimeType: "image/png", buffer: Buffer.from("hello") });
  await expect(page.getByRole("alert")).toContainText("SVG, PNG, JPEG or WebP");

  // The form's Save stays off: a picture is kept on its own.
  await expect(page.getByRole("button", { name: "Save", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Back to design systems" }).click();
  await page.getByRole("listitem").filter({ hasText: name }).getByRole("button", { name: "Edit" }).click();
  await page.getByRole("button", { name: "Assets", exact: true }).click();
  await expect(page.getByLabel("When to use it")).toHaveValue("On dark backgrounds");
  await expect(page.getByLabel("Kind")).toHaveValue("icon");
  await page.getByRole("button", { name: "Remove acme-logo" }).click();
  await expect(page.getByLabel("Picture name")).toHaveCount(0);
});
