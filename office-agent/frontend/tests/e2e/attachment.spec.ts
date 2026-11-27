import path from "node:path";
import { readFileSync, renameSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

test("attaching a file shows a chip and folds a workspace-note into the outgoing message", async ({ page }) => {
  await page.goto(freshThreadPath("attach"));
  await waitForConnected(page);

  const filePath = path.join(__dirname, "fixtures", "sample.txt");
  await page.locator("input[type=file]").setInputFiles(filePath);

  await expect(page.getByText("sample.txt")).toBeVisible();

  await page.locator("textarea").click();
  await page.locator("textarea").fill("please summarize this");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("please summarize this")).toBeVisible();
  // The tray empties once the message sends; what was sent stays in the conversation as a card.
  // (A name the workspace already has is made unique, as "sample (2).txt".)
  await expect(page.getByRole("button", { name: /^Remove sample/ })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^Open sample.*\.txt$/ })).toHaveCount(1);
  // The note that tells the model about the file is not text in the bubble.
  await expect(page.getByText("Attached files, now in the workspace")).toHaveCount(0);
});

test("a sent PDF and a sent file stay in the conversation as cards, also after a reload, and the PDF opens", async ({ page }) => {
  await page.goto(freshThreadPath("attach-sent"));
  await waitForConnected(page);
  const fixtures = path.join(__dirname, "fixtures");
  await page.locator("input[type=file]").setInputFiles(path.join(fixtures, "sample.pdf"));
  await expect(page.getByRole("button", { name: /^Remove sample.*\.pdf$/ })).toBeAttached();
  await page.locator("input[type=file]").setInputFiles(path.join(fixtures, "sample.docx"));
  await expect(page.getByRole("button", { name: /^Remove sample.*\.docx$/ })).toBeAttached();
  await page.getByRole("button", { name: "Send" }).click();
  // Only attachments: no bubble of text, just the cards.
  const pdf = page.getByRole("button", { name: /^Open sample.*\.pdf$/ });
  const docx = page.getByRole("button", { name: /^Open sample.*\.docx$/ });
  await expect(pdf.locator("img")).toBeVisible();
  await expect(docx.getByText("DOCX", { exact: true })).toBeVisible();
  await expect(page.getByText("(attachment sent)")).toHaveCount(0);

  await page.reload();
  await waitForConnected(page);
  await expect(pdf.locator("img")).toBeVisible();
  await expect(docx).toBeVisible();
  await expect(page.getByText("Attached files, now in the workspace")).toHaveCount(0);

  await pdf.click();
  await expect(page.getByRole("dialog").getByText("2 pages")).toBeVisible();
});

test("a PDF opens with all pages and a Word document opens its paginated preview", async ({ page }) => {
  await page.goto(freshThreadPath("attach-view"));
  await waitForConnected(page);

  const fixtures = path.join(__dirname, "fixtures");
  await page.locator("input[type=file]").setInputFiles([path.join(fixtures, "sample.pdf")]);
  const pdf = page.getByRole("button", { name: "Open sample.pdf" });
  await expect(pdf.locator("img")).toBeVisible();
  await expect(pdf.getByText("PDF", { exact: true })).toBeVisible();

  await pdf.click();
  const dialog = page.getByRole("dialog", { name: "sample.pdf" });
  await expect(dialog.getByText("2 pages")).toBeVisible();
  await expect(dialog.locator("img")).toHaveCount(2);
  await dialog.getByRole("button", { name: "Close" }).click();
  await expect(dialog).toHaveCount(0);

  // Right-click on a PDF's page offers copying it.
  await pdf.click({ button: "right" });
  await expect(page.getByRole("menuitem", { name: "Copy Image", exact: true })).toBeVisible();
  await page.keyboard.press("Escape");

  await page.locator("input[type=file]").setInputFiles([path.join(fixtures, "sample.docx")]);
  // CI tests the viewer on a rendered two-page PDF without requiring an installed Office engine.
  await page.route("**/api/attachment/docx?*", (route) => route.fulfill({
    body: readFileSync(path.join(fixtures, "sample.pdf")),
    contentType: "application/pdf",
    headers: { etag: '"sample"' },
  }));
  const docx = page.getByRole("button", { name: "Open sample.docx" });
  await expect(docx.getByText("DOCX", { exact: true })).toBeVisible();
  await docx.click({ button: "right" });
  await expect(page.getByRole("menuitem")).toHaveCount(0);
  await docx.click();
  const word = page.getByRole("dialog", { name: "sample.docx" });
  await expect(word.getByText("Page 1 of 2", { exact: true })).toBeVisible();
  await word.getByRole("region", { name: "Page 2" }).scrollIntoViewIfNeeded();
  await expect(word.getByText("Page 2 of 2", { exact: true })).toBeVisible();
  await word.getByRole("combobox", { name: "Zoom" }).selectOption("125");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("a Word preview follows an atomic save and keeps its page and zoom", async ({ page }) => {
  const workspace = process.env.COSCRIBE_E2E_WORKSPACE;
  test.skip(!workspace, "Requires the backend's shared workspace");
  await page.goto(freshThreadPath("live-word"));
  await waitForConnected(page);
  const fixture = path.join(__dirname, "fixtures", "sample.docx");
  const upload = page.waitForResponse((res) => res.url().endsWith("/api/upload") && res.ok());
  await page.locator("input[type=file]").setInputFiles(fixture);
  const saved = path.join(workspace!, (await (await upload).json()).path);
  const pdf = readFileSync(path.join(__dirname, "fixtures", "sample.pdf"));
  let firstVersion: string | undefined;
  let updates = 0;
  let resume: () => void = () => {};
  const delayed = new Promise<void>((resolve) => { resume = resolve; });
  await page.route("**/api/attachment/docx?*", async (route) => {
    const meta = await route.fetch({ method: "HEAD" });
    const version = meta.headers().etag;
    firstVersion ??= version;
    if (version !== firstVersion) {
      updates += 1;
      await delayed;
    }
    await route.fulfill({
      body: pdf, contentType: "application/pdf", headers: { etag: version },
    });
  });

  await page.getByRole("button", { name: /^Open sample.*\.docx$/ }).click();
  const dialog = page.getByRole("dialog");
  const zoom = dialog.getByRole("combobox", { name: "Zoom" });
  await zoom.selectOption("125");
  await dialog.getByRole("region", { name: "Page 2" }).scrollIntoViewIfNeeded();
  await expect(dialog.getByText("Page 2 of 2", { exact: true })).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Refresh" })).toHaveCount(0);
  try {
    writeFileSync(`${saved}.tmp`, readFileSync(fixture));
    renameSync(`${saved}.tmp`, saved);
    await expect.poll(() => updates).toBeGreaterThan(0);
    await expect(dialog.getByText("Page 2 of 2", { exact: true })).toBeVisible();
    const loaded = page.waitForResponse((res) => res.url().includes("/api/attachment/docx?") && res.request().method() === "POST");
    resume();
    await loaded;
    await expect(dialog.getByText("Page 2 of 2", { exact: true })).toBeVisible();
    await expect(zoom).toHaveValue("125");
  } finally {
    resume();
  }
});

test("an attached and a pasted picture are saved in .coscribe/uploads and the model is told their paths", async ({ page }) => {
  const sent: string[] = [];
  page.on("websocket", (ws) => ws.on("framesent", (frame) => typeof frame.payload === "string" && sent.push(frame.payload)));
  await page.goto(freshThreadPath("attach-pictures"));
  await waitForConnected(page);
  const png = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 8;
    return canvas.toDataURL("image/png").split(",")[1];
  });
  await page.locator('input[type="file"]').first().setInputFiles({ name: "photo.png", mimeType: "image/png", buffer: Buffer.from(png, "base64") });
  await page.locator("textarea").evaluate((box, data) => {
    const bytes = Uint8Array.from(atob(data), (c) => c.charCodeAt(0));
    const clipboard = new DataTransfer();
    clipboard.items.add(new File([bytes], "image.png", { type: "image/png" }));
    box.dispatchEvent(new ClipboardEvent("paste", { clipboardData: clipboard, bubbles: true, cancelable: true }));
  }, png);
  const composer = page.getByTestId("composer");
  await expect(composer.getByRole("button", { name: /^Remove/ })).toHaveCount(2);
  await page.locator("textarea").fill("what is in these");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("what is in these")).toBeVisible();

  const message = sent.map((raw) => JSON.parse(raw) as { type: string; text?: string }).find((m) => m.type === "user_message");
  expect(message?.text).toMatch(
    /\(Attached files, now in the workspace: \.coscribe\/uploads\/images\/photo( \(\d+\))?\.png, \.coscribe\/uploads\/screenshots\/screenshot-\d{4}-\d\d-\d\d-\d{6}( \(\d+\))?\.png\)$/,
  );
  // The pictures show as themselves, not again as file cards, also after a reload.
  await expect(page.getByRole("button", { name: /^Open (photo|screenshot)/ })).toHaveCount(0);
  await page.reload();
  await waitForConnected(page);
  await expect(page.getByRole("img", { name: /^Attachment / })).toHaveCount(2);
  await expect(page.getByRole("button", { name: /^Open (photo|screenshot)/ })).toHaveCount(0);
});
