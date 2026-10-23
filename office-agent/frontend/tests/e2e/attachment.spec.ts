import path from "node:path";
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

test("a PDF shows its first page, opens with all pages, and a file that can't be shown says so", async ({ page }) => {
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
  const docx = page.getByRole("button", { name: "Open sample.docx" });
  await expect(docx.getByText("DOCX", { exact: true })).toBeVisible();
  await docx.click({ button: "right" });
  await expect(page.getByRole("menuitem")).toHaveCount(0);
  await docx.click();
  await expect(page.getByText("File previews are not supported for this file type")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
