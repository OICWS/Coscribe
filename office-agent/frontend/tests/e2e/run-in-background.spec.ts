import { existsSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// A script that is still running can be let go on as a background task: its tool call returns,
// the turn finishes, and the script carries on in the Background tasks.
test("a running script can be moved to the background and keeps running", async ({ page }) => {
  test.setTimeout(240_000);
  const threadPath = freshThreadPath("run-bg");
  const threadId = new URL(threadPath, "http://x").searchParams.get("thread");
  await page.request.post("/api/config", { data: { updates: { COSCRIBE_DEFAULT_PERMISSION_MODE: "manual" } } });
  try {
    await page.goto(threadPath);
    await waitForConnected(page);
    const textarea = page.locator("textarea");

    // The first script of a server builds its Python environment, which can take a while.
    await textarea.fill('warm up [[stub-tool run_python_script {"script":"print(1)","description":"Warm up"}]]');
    await page.keyboard.press("Enter");
    await page.getByRole("button", { name: "Approve", exact: true }).click({ timeout: 30_000 });
    await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 180_000 });

    const script = "import time\\nprint('started', flush=True)\\ntime.sleep(40)\\nprint('finished')";
    await textarea.fill(`slow one [[stub-tool run_python_script {"script":"${script}","description":"A slow script"}]]`);
    await page.keyboard.press("Enter");
    await page.getByRole("button", { name: "Approve", exact: true }).click({ timeout: 30_000 });

    const move = page.getByRole("button", { name: "Run in background" });
    await expect(move).toBeVisible({ timeout: 30_000 });
    await move.click();

    // The call returned, so the turn is over while the script is not.
    await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 30_000 });
    await expect(move).toBeHidden();
    const tasks = await page.request.get(`/api/threads/${threadId}/background-tasks`);
    const [task] = (await tasks.json()) as { status: string; description: string }[];
    expect(task.description).toBe("A slow script");
    expect(task.status).toBe("running");
  } finally {
    await page.request.post("/api/config", { data: { updates: { COSCRIBE_DEFAULT_PERMISSION_MODE: "auto" } } });
  }
});

// Stop ends the script its tool call is still waiting on; it does not run to the end unseen.
test("stopping a turn ends the script it waits on", async ({ page }) => {
  test.setTimeout(240_000);
  const threadPath = freshThreadPath("run-stop");
  const workspace = process.env.COSCRIBE_E2E_WORKSPACE;
  test.skip(!workspace, "needs COSCRIBE_E2E_WORKSPACE, the server's workspace folder");
  await page.request.post("/api/config", { data: { updates: { COSCRIBE_DEFAULT_PERMISSION_MODE: "manual" } } });
  try {
    await page.goto(threadPath);
    await waitForConnected(page);
    const marker = `stop-${Math.random().toString(36).slice(2, 8)}.txt`;
    const script = `import time\\nprint('started', flush=True)\\ntime.sleep(20)\\nopen('${marker}', 'w').write('late')`;
    await page.locator("textarea").fill(`slow [[stub-tool run_python_script {"script":"${script}","description":"A slow script"}]]`);
    await page.keyboard.press("Enter");
    await page.getByRole("button", { name: "Approve", exact: true }).click({ timeout: 30_000 });
    await expect(page.getByRole("button", { name: "Run in background" })).toBeVisible({ timeout: 180_000 });
    await page.getByRole("button", { name: "Stop", exact: true }).click();
    await expect(page.getByRole("button", { name: "Send" })).toBeVisible({ timeout: 30_000 });
    // Past the script's own sleep: had it kept going it would have written the file.
    await page.waitForTimeout(23_000);
    expect(existsSync(join(workspace ?? "", marker))).toBe(false);
  } finally {
    await page.request.post("/api/config", { data: { updates: { COSCRIBE_DEFAULT_PERMISSION_MODE: "auto" } } });
  }
});
