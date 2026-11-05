import { expect, test, type APIRequestContext } from "@playwright/test";

// No model involved: a step that fails is tried again, then the steps in its place run; a step
// that may be skipped is; the run counts as done and the run view and report say how each
// failure was handled (decision 0032). The editor shows the same on the canvas, in the quick edit
// and in the compiled graph.

const missing = (id: string, title: string, onFailure: object) => ({
  id,
  kind: "tool",
  title,
  tool: "read_file",
  args: { path: `e2e-missing-${id}.txt` },
  save_as: id,
  on_failure: onFailure,
});

async function lastRun(request: APIRequestContext, id: string) {
  const tasks = await (await request.get("/api/scheduled-tasks")).json();
  const runs = tasks.find((t: { trigger_id: string }) => t.trigger_id === id).runs;
  return runs[runs.length - 1];
}

test("a failed step tried again and replaced, and a skipped one, don't stop the run", async ({ page }) => {
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e failure handling",
      kind: "manual",
      at: "",
      workflow: {
        inputs: [],
        steps: [
          missing("rates", "Read this month's rates", {
            retries: 1,
            wait_seconds: 0,
            then: "steps",
            steps: [
              { id: "old", kind: "tool", title: "List what is there", tool: "list_files", args: {}, save_as: "rates" },
            ],
          }),
          missing("chat", "Read the chat settings", { retries: 0, wait_seconds: 30, then: "skip", steps: [] }),
        ],
      },
    },
  });
  const task = await created.json();
  expect(task.trigger_id, JSON.stringify(task)).toBeTruthy();
  try {
    await page.goto(`/?view=scheduled&task=${task.trigger_id}`);
    const rates = page.locator('[data-canvas-step="rates"]');
    await expect(rates).toContainText("If it fails: 1 more try, then run 1 other step");
    await expect(page.locator('[data-canvas-step="chat"]')).toContainText("If it fails: skip it");

    await page.locator('[data-canvas-step="chat"]').click();
    const sheet = page.getByRole("complementary", { name: "Change this step" });
    await expect(sheet.getByText("If it fails", { exact: true })).toBeVisible();
    await expect(sheet.getByLabel("Then")).toHaveText("Skip it and go on");
    await sheet.getByRole("button", { name: "Close" }).click();

    await page.request.post(`/api/scheduled-tasks/${task.trigger_id}/run`, { data: {} });
    await expect
      .poll(async () => (await lastRun(page.request, task.trigger_id))?.status, { timeout: 30_000 })
      .toBe("completed");
    const run = await lastRun(page.request, task.trigger_id);
    await page.goto(`/?thread=scheduled-${task.trigger_id}-${run.run_id}`);
    const row = page.locator('[data-run-step="rates"]');
    await expect(row).toContainText("Failed, ran other steps in its place · after 2 tries");
    await expect(row.getByRole("region", { name: "If it fails" })).toContainText("List what is there");
    await expect(page.locator('[data-run-step="chat"]')).toContainText("Failed, skipped");
    await expect(page.getByTestId("run-report")).toContainText("Failed without stopping the run");
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
  }
});
