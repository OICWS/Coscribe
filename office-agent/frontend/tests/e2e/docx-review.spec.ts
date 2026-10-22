import { execFileSync } from "node:child_process";
import { copyFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// The Word panel's review actions against the real server: each step checks the review the
// server reads back from the file, not only what the screen shows. The file is built into the
// server's workspace by fixtures/build_redline.py, and the stub model "reads" it so it appears
// among the thread's files.
const WORKSPACE = process.env.COSCRIBE_E2E_WORKSPACE;
const AGENT = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

test.skip(!WORKSPACE, "COSCRIBE_E2E_WORKSPACE names the server's workspace folder");
test.use({ viewport: { width: 1600, height: 1200 } });

interface Review {
  changes: { id: string; kind: string }[];
  comments: { id: string; text: string; done: boolean; replies: { text: string }[] }[];
}

const threadOf = (page: Page) => new URL(page.url()).searchParams.get("thread") ?? "";

async function openRedline(page: Page, name: string) {
  execFileSync("python", [join("frontend", "tests", "e2e", "fixtures", "build_redline.py"), WORKSPACE ?? "", name], {
    cwd: AGENT,
    env: { ...process.env, PYTHONPATH: AGENT },
  });
  await page.goto(freshThreadPath("docx-review"));
  await waitForConnected(page);
  await page.locator("textarea").fill(`open it [[stub-tool read_docx {"path":"${name}.docx"}]]`);
  await page.keyboard.press("Enter");
  await page.getByTitle("Show task details").click();
  await page.getByRole("button", { name: `${name}.docx Read` }).click();
  await page.getByRole("button", { name: "Expand Viewer" }).click();
  await expect(page.locator(".docx-page section.docx")).toBeVisible();
}

const reviewOf = async (page: Page, name: string): Promise<Review> => {
  const response = await page.request.get(`/api/threads/${threadOf(page)}/docx-review?path=${name}.docx`);
  expect(response.ok()).toBe(true);
  return response.json();
};

test("the Word panel accepts and rejects tracked changes, checked on the server", async ({ page }) => {
  const name = `redline-${Math.random().toString(36).slice(2, 8)}`;
  await openRedline(page, name);
  expect((await reviewOf(page, name)).changes.map((c) => c.kind).sort()).toEqual(["delete", "insert"]);

  await test.step("a selected change is accepted and the other is left", async () => {
    await page.locator(".docx-page ins").first().click();
    await page.getByRole("button", { name: "Accept", exact: true }).click();
    await expect.poll(async () => (await reviewOf(page, name)).changes.map((c) => c.kind)).toEqual(["delete"]);
    await expect(page.locator(".docx-page ins")).toHaveCount(0);
    await expect(page.locator(".docx-page del")).toHaveCount(1);
    await expect(page.locator(".docx-page")).toContainText("(extended)");
  });

  await test.step("a refused action shows the server's reason and changes nothing", async () => {
    await page.route("**/docx-review", (route) =>
      route.request().method() === "POST"
        ? route.fulfill({ status: 400, json: { error: "no tracked change with id 99" } })
        : route.continue(),
    );
    await page.locator(".docx-page del").first().click();
    await page.getByRole("button", { name: "Reject", exact: true }).click();
    await expect(page.getByText("no tracked change with id 99")).toBeVisible();
    expect((await reviewOf(page, name)).changes).toHaveLength(1);
    await page.unroute("**/docx-review");
  });

  await test.step("Reject all asks first, then settles every change", async () => {
    await page.getByRole("button", { name: "Reject all", exact: true }).click();
    await page.getByRole("button", { name: "Cancel" }).click();
    expect((await reviewOf(page, name)).changes).toHaveLength(1);
    await page.getByRole("button", { name: "Reject all", exact: true }).click();
    await page.getByRole("dialog").or(page.locator("div.fixed")).getByRole("button", { name: "Reject all" }).click();
    await expect.poll(async () => (await reviewOf(page, name)).changes).toEqual([]);
    await expect(page.locator(".docx-page del")).toHaveCount(0);
    await expect(page.locator(".docx-page")).toContainText("The total price is 100 dollars");
  });
});

test("the Word panel replies to, resolves, reopens and adds comments, checked on the server", async ({ page }) => {
  const name = `redline-${Math.random().toString(36).slice(2, 8)}`;
  await openRedline(page, name);
  const card = page.locator("article.absolute").filter({ hasText: "Final price?" });

  await test.step("a reply is added to the thread", async () => {
    await card.click();
    await card.getByLabel("Reply").fill("It is 120 dollars");
    await card.getByRole("button", { name: "Reply", exact: true }).click();
    await expect.poll(async () => (await reviewOf(page, name)).comments[0].replies.map((r) => r.text)).toEqual([
      "It is 120 dollars",
    ]);
    await expect(card).toContainText("It is 120 dollars");
  });

  await test.step("the thread is resolved and then reopened", async () => {
    await card.click();
    await card.getByRole("button", { name: "Resolve" }).click();
    await expect.poll(async () => (await reviewOf(page, name)).comments[0].done).toBe(true);
    await card.getByRole("button", { name: "Reopen" }).click();
    await expect.poll(async () => (await reviewOf(page, name)).comments[0].done).toBe(false);
  });

  await test.step("a comment is added on selected words", async () => {
    await page.evaluate(() => {
      const para = [...document.querySelectorAll(".docx-page p")].find((p) =>
        p.textContent?.includes("The agreement runs for one year."),
      );
      document.getSelection()?.selectAllChildren(para as Element);
    });
    await page.getByLabel("New comment").fill("Make it two years");
    await page.getByRole("button", { name: "Comment", exact: true }).click();
    await expect.poll(async () => (await reviewOf(page, name)).comments.map((c) => c.text)).toContain("Make it two years");
  });

  await test.step("a refused comment shows the server's reason", async () => {
    await page.evaluate(() => {
      const para = [...document.querySelectorAll(".docx-page p")].find((p) => p.textContent?.includes("Service agreement"));
      document.getSelection()?.selectAllChildren(para as Element);
    });
    await page.route("**/docx-review", (route) =>
      route.request().method() === "POST"
        ? route.fulfill({ status: 400, json: { error: "those words appear twice" } })
        : route.continue(),
    );
    await page.getByLabel("New comment").fill("Nope");
    await page.getByRole("button", { name: "Comment", exact: true }).click();
    await expect(page.getByText("those words appear twice")).toBeVisible();
    await page.unroute("**/docx-review");
  });

  await test.step("Ask coscribe sends the selected words with their file and page to the conversation", async () => {
    await page.evaluate(() => {
      const para = [...document.querySelectorAll(".docx-page p")].find((p) => p.textContent?.includes("Service agreement"));
      document.getSelection()?.selectAllChildren(para as Element);
    });
    await page.getByRole("button", { name: "Ask coscribe" }).click();
    // The expanded viewer covers the chat, so the bubble is in the page but not visible.
    await expect(page.getByText(`Question about ${name}.docx, page 1:`)).toContainText("> Service agreement");
  });
});

test("a document with no comments sits in the middle of the panel, with no empty rail beside it", async ({ page }) => {
  const name = `plain-${Math.random().toString(36).slice(2, 8)}`;
  copyFileSync(join(AGENT, "frontend", "tests", "e2e", "fixtures", "sample.docx"), join(WORKSPACE ?? "", `${name}.docx`));
  await page.goto(freshThreadPath("docx-plain"));
  await waitForConnected(page);
  await page.locator("textarea").fill(`open it [[stub-tool read_docx {"path":"${name}.docx"}]]`);
  await page.keyboard.press("Enter");
  await page.getByTitle("Show task details").click();
  await page.getByRole("button", { name: `${name}.docx Read` }).click();
  await page.getByRole("button", { name: "Expand Viewer" }).click();
  const sheet = page.locator(".docx-page section.docx");
  await expect(sheet).toBeVisible();
  const scroller = (await page.locator(".docx-viewer").boundingBox())!;
  const box = (await sheet.boundingBox())!;
  const left = box.x - scroller.x;
  const right = scroller.x + scroller.width - (box.x + box.width);
  expect(Math.abs(left - right)).toBeLessThan(40);
});
