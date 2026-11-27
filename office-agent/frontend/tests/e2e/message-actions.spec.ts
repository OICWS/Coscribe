import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

async function send(page: Page, text: string): Promise<void> {
  const textarea = page.getByTestId("composer").locator("textarea");
  await textarea.fill(text);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 60_000 });
}

const bubble = (page: Page, text: string) => page.getByTestId("chat-log").getByText(text, { exact: true });

test("a sent message shows its time, and Rewind takes it and what follows out", async ({ page }) => {
  const path = freshThreadPath("rewind");
  await page.goto(path);
  await waitForConnected(page);
  await send(page, "Reply with the single word: first");
  await send(page, "Reply with the single word: second");

  await bubble(page, "Reply with the single word: second").hover();
  await expect(page.getByText("just now").last()).toBeVisible();
  await page.getByRole("button", { name: "Rewind to here" }).last().click();

  await expect(bubble(page, "Reply with the single word: second")).toHaveCount(0);
  await expect(page.getByTestId("composer").locator("textarea")).toHaveValue("Reply with the single word: second");

  // The server cut its history too: a reload replays only the first turn.
  await page.goto(path);
  await waitForConnected(page);
  await expect(bubble(page, "Reply with the single word: first")).toBeVisible();
  await expect(bubble(page, "Reply with the single word: second")).toHaveCount(0);
});

test("editing an earlier message runs from it and drops the turns after it", async ({ page }) => {
  const path = freshThreadPath("edit");
  await page.goto(path);
  await waitForConnected(page);
  await send(page, "Reply with the single word: alpha");
  await send(page, "Reply with the single word: beta");

  await bubble(page, "Reply with the single word: alpha").hover();
  await page.getByRole("button", { name: "Edit", exact: true }).first().click();
  const box = page.getByRole("textbox", { name: "Edit message" });
  await expect(page.getByRole("button", { name: "Save" })).toBeDisabled();
  await box.fill("Reply with the single word: gamma");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 60_000 });

  await page.goto(path);
  await waitForConnected(page);
  await expect(bubble(page, "Reply with the single word: gamma")).toBeVisible();
  await expect(bubble(page, "Reply with the single word: alpha")).toHaveCount(0);
  await expect(bubble(page, "Reply with the single word: beta")).toHaveCount(0);
});

test("a message added while working has its time and Copy after delivery and reload", async ({ page, context }) => {
  const path = freshThreadPath("steer-actions");
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const setMode = (mode: string) =>
    page.request.post("/api/config", { data: { updates: { COSCRIBE_DEFAULT_PERMISSION_MODE: mode } } });
  expect((await setMode("manual")).ok()).toBe(true);
  try {
    await page.goto(path);
    await waitForConnected(page);
    const composer = page.getByTestId("composer").locator("textarea");
    await composer.fill('[[stub-tool write_file {"path":"steer-actions.txt","content":"hello"}]]');
    await page.keyboard.press("Enter");
    const approve = page.getByRole("button", { name: "Approve", exact: true });
    await expect(approve).toBeVisible();

    // Plain text answers the pending approval. An attachment queues the message for the next step.
    await page.getByTestId("composer").locator("input[type=file]").setInputFiles({
      name: "steer-note.txt", mimeType: "text/plain", buffer: Buffer.from("Supporting figures"),
    });
    await expect(page.getByText("steer-note.txt", { exact: true })).toBeVisible();
    const note = "Also check the numbers.";
    await composer.fill(note);
    await page.keyboard.press("Enter");
    const row = page.locator('[class~="group/msg"]').filter({ has: page.getByText(note, { exact: true }) });
    await expect(row.getByRole("button", { name: "Interrupt the reply and send this now" })).toBeVisible();
    await approve.click();
    await expect(page.getByRole("button", { name: "Send", exact: true })).toBeVisible();

    const timeTip = row.getByRole("tooltip").filter({ hasText: "Added while working" });
    const checkToolbar = async () => {
      await bubble(page, note).hover();
      await expect(row.getByRole("button", { name: "Rewind to here" })).toBeDisabled();
      const edit = row.getByRole("button", { name: "Edit", exact: true });
      await expect(edit).toBeDisabled();
      await edit.hover();
      await expect(row.getByRole("tooltip").filter({ hasText: "can’t be edited or rewound separately" }).last()).toHaveCSS("opacity", "1");
      await row.getByText("just now", { exact: true }).hover();
      await expect(timeTip).toHaveCSS("opacity", "1");
      return timeTip.textContent();
    };
    const before = await checkToolbar();
    await row.locator('button[title=""]').click();
    await expect(row.locator('button[title="Copied"]')).toBeVisible();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(note);

    await page.goto(path);
    await waitForConnected(page);
    expect(await checkToolbar()).toBe(before);
  } finally {
    await setMode("auto");
  }
});
