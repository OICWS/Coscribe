import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// A reply that names a file the conversation made shows a chip with a hover card, and the end of the
// turn a card that opens it (the stub model writes the document, then says its name).
test.skip(!process.env.COSCRIBE_E2E_WORKSPACE, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({ viewport: { width: 1600, height: 1000 } });

// A name in Chinese is percent-encoded by the markdown pipeline on its way to the chip.
for (const prefix of ["made", "AI新闻月报"]) {
test(`a file named in a reply is a chip with a card on hover, and the turn ends with a card that opens it (${prefix})`, async ({ page }) => {
  const name = `${prefix}-${Math.random().toString(36).slice(2, 8)}`;
  await page.goto(freshThreadPath("chat-files"));
  await waitForConnected(page);
  await page.locator("textarea").fill(`write it [[stub-tool write_docx {"path":"${name}.docx","content":"# Title\\n\\nBody"}]] [[stub-say I wrote ${name}.docx for you.]]`);
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Approve", exact: true }).click();

  const chip = page.locator("p").getByRole("button", { name });
  await expect(chip).toBeVisible();
  await chip.hover();
  const card = page.getByRole("tooltip");
  await expect(card).toContainText("Document");
  await expect(card).toContainText(name);

  // The chip opens the file too, not a file named by its encoded address.
  await page.mouse.move(5, 500);
  await chip.click();
  await expect(page.getByRole("region", { name: "Viewer" })).toBeVisible();

  const end = page.getByTitle(`Open ${name}.docx`);
  await expect(end).toBeVisible();
  await expect(end).toContainText("Document · .docx");
  await page.mouse.move(5, 500);
  await end.click();
  await expect(page.getByRole("region", { name: "Viewer" })).toBeVisible();
});
}
