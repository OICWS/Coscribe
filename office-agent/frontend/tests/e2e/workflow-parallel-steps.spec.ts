import { expect, test } from "@playwright/test";

// No model involved: a step runs two lanes at the same time (decision 0036). The task page draws
// them side by side; a run waits for an approval in one lane after the other has ended, the run
// page shows each lane's steps under its name, and approving it lets the run go on.

test("a parallel step runs its lanes and waits for an approval inside one", async ({ page }) => {
  const workflow = {
    inputs: [],
    steps: [
      {
        id: "both",
        kind: "parallel",
        title: "Both at once",
        lanes: [
          { label: "Ask", steps: [{ id: "ok", kind: "approval", title: "Check it", message: "Go on?" }] },
          {
            label: "Look",
            steps: [
              { id: "list", kind: "tool", title: "List the workspace", tool: "list_files", args: {}, save_as: "found" },
            ],
          },
        ],
      },
      { id: "after", kind: "tool", title: "List again", tool: "list_files", args: {}, save_as: "again" },
    ],
  };
  const made = await (
    await page.request.post("/api/scheduled-tasks", {
      data: { name: "e2e parallel", kind: "manual", at: "", workflow },
    })
  ).json();
  const id = made.trigger_id;
  expect(id, JSON.stringify(made)).toBeTruthy();
  const lastRun = async () => {
    const tasks = await (await page.request.get("/api/scheduled-tasks")).json();
    const runs = tasks.find((t: { trigger_id: string }) => t.trigger_id === id).runs;
    return runs[runs.length - 1];
  };
  try {
    await page.goto(`/?view=scheduled&task=${id}`);
    const both = page.locator('[data-plain-step="both"]');
    await expect(both).toContainText("At the same time");
    await page.getByRole("button", { name: "Show the flowchart" }).click();
    await expect(page.getByTestId("parallel-lanes")).toContainText("All 2 lanes run at the same time");
    await expect(page.locator('[data-canvas-step="both"]')).toContainText("Does 2 things at the same time");

    await page.request.post(`/api/scheduled-tasks/${id}/run`, { data: {} });
    await expect.poll(async () => (await lastRun()).status, { timeout: 30_000 }).toBe("needs_approval");
    const run = await lastRun();
    await page.goto(`/?thread=scheduled-${id}-${run.run_id}`);
    // The simple view: the lane's approval opens in the step list, under the step that runs both.
    const running = page.locator('[data-run-row="both"]');
    await expect(running).toHaveAttribute("data-run-status", "waiting", { timeout: 30_000 });
    await expect(page.getByTestId("run-result")).toContainText("Waiting for your OK at");
    await expect(running.locator('[data-run-row="list"]')).toHaveAttribute("data-run-status", "done");
    await running.getByRole("button", { name: "Approve and continue" }).click();
    await expect.poll(async () => (await lastRun()).status, { timeout: 30_000 }).toBe("completed");
    await expect(page.getByTestId("run-result")).toContainText("Done", { timeout: 30_000 });
    await expect(running).toHaveAttribute("data-run-status", "done");

    await page.getByRole("button", { name: "Detailed", exact: true }).click();
    await expect(page.locator('[data-run-step="both"]').first()).toContainText("All 2 lanes ended");
    await expect(page.getByRole("region", { name: "Look" })).toContainText("List the workspace");
    const done = (await lastRun()).steps.filter((s: { status: string }) => s.status === "done");
    expect(done.map((s: { step_id: string }) => s.step_id).sort()).toEqual(["after", "both", "list", "ok"]);
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${id}`);
  }
});
