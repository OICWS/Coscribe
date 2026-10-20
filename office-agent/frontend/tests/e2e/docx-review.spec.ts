import { execFileSync } from "node:child_process";
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
  comments: { id: string; text: string }[];
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
