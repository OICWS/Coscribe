import { expect, test, type APIRequestContext } from "@playwright/test";

// No model involved: a run stops at a step that asks for values, the person fills them in the
// run view and it goes on; then it waits at a wait step until the person says go on now
// (decision 0033). The canvas says what each step asks for and how long it waits.

async function lastRun(request: APIRequestContext, id: string) {
  const tasks = await (await request.get("/api/scheduled-tasks")).json();
  const runs = tasks.find((t: { trigger_id: string }) => t.trigger_id === id).runs;
  return runs[runs.length - 1];
}

test("a run asks for values, then waits until told to go on", async ({ page }) => {
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e ask and wait",
      kind: "manual",
      at: "",
      workflow: {
        inputs: [],
        steps: [
          {
            id: "ask",
            kind: "ask",
            title: "Ask for the limit",
            message: "What limit should this month use?",
            save_as: "got",
            fields: [
              { name: "limit", label: "Limit", type: "number" },
              { name: "team", label: "Team", type: "choice", options: ["Sales", "Support"], default: "Sales" },
            ],
          },
          { id: "later", kind: "wait", title: "Wait for the bank", until: "duration", minutes: 600 },
          { id: "list", kind: "tool", title: "List what is there", tool: "list_files", args: {}, save_as: "files" },
        ],
      },
    },
  });
  const task = await created.json();
  expect(task.trigger_id, JSON.stringify(task)).toBeTruthy();
  try {
    await page.goto(`/?view=scheduled&task=${task.trigger_id}`);
    await expect(page.locator('[data-plain-step="ask"]')).toContainText("Asks you for “Limit” and “Team”");
    await expect(page.locator('[data-plain-step="later"]')).toContainText("Waits 10 hours");

    await page.request.post(`/api/scheduled-tasks/${task.trigger_id}/run`, { data: {} });
    await expect
      .poll(async () => (await lastRun(page.request, task.trigger_id))?.status, { timeout: 30_000 })
      .toBe("needs_approval");
    const run = await lastRun(page.request, task.trigger_id);
    await page.goto(`/?thread=scheduled-${task.trigger_id}-${run.run_id}`);

    const ask = page.getByTestId("ask-card");
    await expect(ask).toContainText("What limit should this month use?");
    await expect(ask.getByRole("button", { name: "Continue" })).toBeDisabled();
    await expect(ask).toContainText("Still needed: Limit");
    await ask.getByLabel("Limit").fill("250");
    await ask.getByRole("button", { name: "Continue" }).click();

    const wait = page.getByTestId("wait-card");
    await expect(wait).toBeVisible({ timeout: 30_000 });
    await expect(wait).toContainText("Waiting until");
    expect((await lastRun(page.request, task.trigger_id)).status).toBe("waiting");
    await wait.getByRole("button", { name: "Go on now" }).click();

    await expect
      .poll(async () => (await lastRun(page.request, task.trigger_id))?.status, { timeout: 30_000 })
      .toBe("completed");
    await page.getByRole("button", { name: "Detailed", exact: true }).click();
    await expect(page.locator('[data-run-step="ask"]')).toContainText("Answered · Limit: 250 · Team: Sales");
    await expect(page.locator('[data-run-step="later"]')).toContainText("Waited 10 hours");
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
  }
});
