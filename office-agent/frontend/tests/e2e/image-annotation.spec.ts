import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// A picture put in the message box can be opened and drawn on; Save puts the marked copy beside the
// original, and the original stays.
test.use({ viewport: { width: 1400, height: 1000 } });

test("an attached picture is opened, drawn on and saved as a new attachment beside the original", async ({ page }) => {
  await page.goto(freshThreadPath("annotate"));
  await waitForConnected(page);
  const png = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 480;
    canvas.height = 320;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#dbe7f5";
    ctx.fillRect(0, 0, 480, 320);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  await page.locator('input[type="file"]').first().setInputFiles({ name: "board.png", mimeType: "image/png", buffer: Buffer.from(png, "base64") });

  const composer = page.getByTestId("composer");
  await composer.getByRole("button", { name: "Open board.png" }).click();
  const dialog = page.getByRole("dialog", { name: "board.png" });
  await dialog.getByRole("button", { name: "Annotate image" }).click();

  const toolbar = page.getByRole("toolbar", { name: "Annotate" });
  await expect(toolbar).toBeVisible();
  // A clicked tool does not close the dialog under it.
  await toolbar.getByRole("button", { name: "Shape" }).click();
  await page.getByRole("menuitemradio", { name: "Step" }).click();
  await expect(dialog).toBeVisible();

  const area = page.getByLabel("Drawing area");
  const box = (await area.boundingBox())!;
  await page.mouse.click(box.x + 60, box.y + 60);
  await page.mouse.click(box.x + 160, box.y + 90);
  await toolbar.getByRole("button", { name: "Pen" }).click();
  await page.mouse.move(box.x + 100, box.y + 200);
  await page.mouse.down();
  await page.mouse.move(box.x + 260, box.y + 240, { steps: 6 });
  await page.mouse.up();
  await toolbar.getByRole("button", { name: "Undo" }).click();
  await expect(toolbar.getByRole("button", { name: "Redo" })).toBeEnabled();
  await toolbar.getByRole("button", { name: "Redo" }).click();

  await toolbar.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByTestId("image-annotator")).toHaveCount(0);
  await expect(dialog).toHaveCount(0);
  await expect(composer.getByRole("button", { name: "Open board.png" })).toHaveCount(1);
  await expect(composer.getByRole("button", { name: "Open board-annotated.jpg" })).toHaveCount(1);
});
