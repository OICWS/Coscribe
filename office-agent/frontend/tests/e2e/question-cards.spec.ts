import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// A question card sits in the conversation and doesn't hold the turn (decision 0060). The stub
// model asks with the card's own tool, so these run without a real model.

async function send(page: Page, text: string): Promise<void> {
  await page.getByTestId("composer").locator("textarea").fill(text);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 60_000 });
}

const ask = (questions: unknown[]) => `[[stub-tool ask_user_question ${JSON.stringify({ questions })}]]`;

const audience = {
  question: "Who is the deck for?",
  options: [{ label: "Management", description: "8 slides", recommended: true }, { label: "Team" }],
};
const colors = { question: "Which colors?", options: [{ label: "Brand" }, { label: "Plain" }] };

test("one question answers on a click and folds to the answer", async ({ page }) => {
  await page.goto(freshThreadPath("qcard-one"));
  await waitForConnected(page);
  await send(page, ask([audience]));

  const log = page.getByTestId("chat-log");
  await expect(log.getByText("Who is the deck for?", { exact: true })).toBeVisible();
  await expect(log.getByText("Recommended", { exact: true })).toBeVisible();
  await expect(log.getByRole("button", { name: "reply in chat" })).toBeVisible();
  await expect(log.getByRole("button", { name: "Submit" })).toHaveCount(0);
  // The turn ended with the card open: the message box can send again.
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible();

  await log.getByRole("button", { name: /Team/ }).click();
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 60_000 });
  await expect(log.getByLabel("Answered")).toBeVisible();
  await expect(log.getByRole("button", { name: /Management/ })).toHaveCount(0);
  // The click went out as a message, drawn as the card rather than as a bubble.
  await expect(log.getByText("[Answers to your question card]", { exact: false })).toHaveCount(0);
});

test("several questions page, Submit shows once all are answered, and the card lists the answers", async ({ page }) => {
  await page.goto(freshThreadPath("qcard-many"));
  await waitForConnected(page);
  await send(page, ask([audience, colors]));

  const log = page.getByTestId("chat-log");
  await expect(log.getByText("1 / 2", { exact: true })).toBeVisible();
  await log.getByRole("button", { name: /Management/ }).click();
  await expect(log.getByText("Which colors?", { exact: true })).toBeVisible();
  await expect(log.getByRole("button", { name: "Submit" })).toHaveCount(0);
  await log.getByLabel("Your own answer").fill("Dark blue");
  await log.getByRole("button", { name: "Submit" }).click();

  await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 60_000 });
  await expect(log.getByText("Dark blue", { exact: true })).toBeVisible();
  await expect(log.getByText("Management", { exact: true })).toBeVisible();
  await expect(log.getByRole("button", { name: "Submit" })).toHaveCount(0);
});

test("an unrelated message leaves the card open, an answer in words closes it, and a newer card replaces an open one", async ({ page }) => {
  await page.goto(freshThreadPath("qcard-chat"));
  await waitForConnected(page);
  const log = page.getByTestId("chat-log");

  await send(page, ask([audience]));
  await send(page, "What time is it?");
  await expect(log.getByRole("button", { name: /Team/ })).toBeVisible();

  await send(page, `For my boss [[stub-tool answer_question_card {"answers": ["Management"]}]]`);
  await expect(log.getByText("Answered in chat", { exact: true })).toBeVisible();
  await expect(log.getByRole("button", { name: /Team/ })).toHaveCount(0);

  await send(page, ask([colors]));
  await send(page, ask([{ ...colors, question: "Which font?" }]));
  await expect(log.getByText("No longer needed", { exact: false })).toBeVisible();
  await expect(log.getByText("Which font?", { exact: true })).toBeVisible();
});
